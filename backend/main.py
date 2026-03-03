import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent.graph import create_agent
from agent.session import SessionManager
from config import (
    COLLECTION_NAMES,
    EMBEDDING_DIMENSIONS,
    EmbeddingModel,
    settings,
)
from embeddings.registry import EmbeddingRegistry
from ingestion.excel_loader import load_properties
from ingestion.indexer import index_properties
from search.query_parser import QueryParser
from search.searcher import SearchResult, Searcher
from vectorstore.qdrant_manager import QdrantManager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

qdrant_manager: QdrantManager
embedding_registry: EmbeddingRegistry
query_parser: QueryParser
agent_graph: Any
session_manager: SessionManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global qdrant_manager, embedding_registry, query_parser, agent_graph, session_manager

    qdrant_manager = QdrantManager(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )
    embedding_registry = EmbeddingRegistry(settings)
    query_parser = QueryParser(settings)
    session_manager = SessionManager()

    await qdrant_manager.ensure_all_collections()

    agent_graph = create_agent(
        settings=settings,
        query_parser=query_parser,
        embedding_registry=embedding_registry,
        qdrant_manager=qdrant_manager,
    )

    yield

    await qdrant_manager.close()


app = FastAPI(
    title="RAG Properties",
    description="Búsqueda semántica de propiedades inmobiliarias en México",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/qdrant")
async def health_qdrant() -> dict[str, object]:
    collections = {}
    for model in EmbeddingModel:
        info = await qdrant_manager.collection_info(model)
        collections[model.value] = info
    return {"status": "ok", "collections": collections}


@app.get("/models")
async def list_models() -> list[dict[str, object]]:
    return [
        {
            "id": model.value,
            "collection": COLLECTION_NAMES[model],
            "dimensions": EMBEDDING_DIMENSIONS[model],
            "is_default": model == settings.default_embedding_model,
        }
        for model in EmbeddingModel
    ]


@app.post("/ingest")
async def ingest(
    model: EmbeddingModel = settings.default_embedding_model,
    all_models: bool = False,
) -> dict[str, object]:
    """Load properties from Excel and index into Qdrant.

    Args:
        model: Embedding model to use (ignored if all_models=True).
        all_models: If True, index into all 3 model collections.
    """
    excel_path = Path(settings.excel_path)
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail=f"Excel file not found: {excel_path}")

    properties = load_properties(str(excel_path))
    if not properties:
        raise HTTPException(status_code=400, detail="No properties loaded from Excel")

    models_to_index = list(EmbeddingModel) if all_models else [model]
    results: list[dict[str, object]] = []

    for m in models_to_index:
        await qdrant_manager.ensure_collection(m)
        provider = embedding_registry.get(m)
        count = await index_properties(properties, provider, qdrant_manager)
        results.append({
            "model": m.value,
            "collection": COLLECTION_NAMES[m],
            "points_indexed": count,
        })

    if len(results) == 1:
        return results[0]
    return {"results": results}


class SearchRequest(BaseModel):
    query: str
    model: EmbeddingModel = settings.default_embedding_model
    top_k: int = settings.search_top_k


@app.post("/search")
async def search(request: SearchRequest) -> SearchResult:
    """Search properties using natural language.

    The query is parsed by an LLM to extract structured filters (city, bedrooms,
    price range, etc.), then a vector search runs against the filtered candidates.
    """
    parse_start = time.perf_counter()
    parsed = await query_parser.parse(request.query)
    parse_time_ms = (time.perf_counter() - parse_start) * 1000

    provider = embedding_registry.get(request.model)
    searcher = Searcher(
        client=qdrant_manager.client,
        provider=provider,
        top_k=request.top_k,
    )

    return await searcher.search(request.query, parsed, parse_time_ms=parse_time_ms)


# ---------------------------------------------------------------------------
# Chat endpoints (conversational agent)
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    model: EmbeddingModel = settings.default_embedding_model
    top_k: int = settings.search_top_k


@app.post("/chat")
async def chat(request: ChatRequest):
    """Conversational property search via SSE streaming.

    Events emitted: token, tool_start, results, filters, disambiguation,
    state_results, metrics, done, error.
    """
    # Get or create session
    session = None
    if request.session_id:
        session = session_manager.get(request.session_id)
    if not session:
        session = session_manager.create(
            model=request.model.value,
            session_id=request.session_id,
        )

    config = {"configurable": {"thread_id": session.session_id}}

    async def event_generator():
        # Emit session_id first so frontend can track it
        yield {
            "event": "session",
            "data": json.dumps({"session_id": session.session_id}),
        }

        try:
            input_message = HumanMessage(content=request.message)

            async for event in agent_graph.astream_events(
                {"messages": [input_message]},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if isinstance(chunk, AIMessageChunk) and chunk.content:
                        yield {
                            "event": "token",
                            "data": json.dumps(chunk.content, ensure_ascii=False),
                        }

                elif kind == "on_tool_start":
                    yield {
                        "event": "tool_start",
                        "data": json.dumps(
                            {
                                "name": event.get("name", ""),
                                "args": data.get("input", {}),
                            },
                            ensure_ascii=False,
                        ),
                    }

                elif kind == "on_tool_end":
                    tool_output = data.get("output")
                    if tool_output:
                        # tool_output is a ToolMessage; parse its content
                        content = (
                            tool_output.content
                            if hasattr(tool_output, "content")
                            else str(tool_output)
                        )
                        try:
                            parsed = json.loads(content)
                            if "results" in parsed:
                                yield {
                                    "event": "results",
                                    "data": json.dumps(
                                        parsed["results"], ensure_ascii=False
                                    ),
                                }
                            if "parsed_filters" in parsed:
                                yield {
                                    "event": "filters",
                                    "data": json.dumps(
                                        parsed["parsed_filters"], ensure_ascii=False
                                    ),
                                }
                            if "disambiguation" in parsed:
                                yield {
                                    "event": "disambiguation",
                                    "data": json.dumps(
                                        parsed["disambiguation"], ensure_ascii=False
                                    ),
                                }
                            if "state_results" in parsed:
                                yield {
                                    "event": "state_results",
                                    "data": json.dumps(
                                        parsed["state_results"], ensure_ascii=False
                                    ),
                                }
                            if "metrics" in parsed:
                                yield {
                                    "event": "metrics",
                                    "data": json.dumps(
                                        parsed["metrics"], ensure_ascii=False
                                    ),
                                }
                        except (json.JSONDecodeError, TypeError):
                            pass

            yield {"event": "done", "data": ""}

        except Exception as e:
            logger.exception("Chat stream error")
            yield {
                "event": "error",
                "data": json.dumps(str(e), ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


@app.get("/chat/{session_id}/history")
async def chat_history(session_id: str):
    """Get message history for a chat session."""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config = {"configurable": {"thread_id": session_id}}
    state = await agent_graph.aget_state(config)

    messages = []
    for msg in state.values.get("messages", []):
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})

    return {"session_id": session_id, "messages": messages}


@app.delete("/chat/{session_id}")
async def delete_chat(session_id: str):
    """Delete a chat session."""
    deleted = session_manager.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}
