from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import (
    COLLECTION_NAMES,
    EMBEDDING_DIMENSIONS,
    EmbeddingModel,
    settings,
)
from embeddings.registry import EmbeddingRegistry
from vectorstore.qdrant_manager import QdrantManager

qdrant_manager: QdrantManager
embedding_registry: EmbeddingRegistry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global qdrant_manager, embedding_registry

    qdrant_manager = QdrantManager(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )
    embedding_registry = EmbeddingRegistry(settings)

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
