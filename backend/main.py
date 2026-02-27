import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

qdrant_manager: QdrantManager
embedding_registry: EmbeddingRegistry
query_parser: QueryParser


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global qdrant_manager, embedding_registry, query_parser

    qdrant_manager = QdrantManager(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )
    embedding_registry = EmbeddingRegistry(settings)
    query_parser = QueryParser(settings)

    await qdrant_manager.ensure_all_collections()

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
    allow_credentials=True,
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
