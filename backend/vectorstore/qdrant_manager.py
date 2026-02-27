import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    TextIndexParams,
    TokenizerType,
    VectorParams,
)

from config import COLLECTION_NAMES, EMBEDDING_DIMENSIONS, EmbeddingModel

logger = logging.getLogger(__name__)

PAYLOAD_INDEXES: dict[str, PayloadSchemaType | TextIndexParams] = {
    "city": PayloadSchemaType.KEYWORD,
    "state": PayloadSchemaType.KEYWORD,
    "neighborhood": TextIndexParams(
        type="text",
        tokenizer=TokenizerType.MULTILINGUAL,
        min_token_len=2,
        max_token_len=20,
    ),
    "property_type": PayloadSchemaType.KEYWORD,
    "operation": PayloadSchemaType.KEYWORD,
    "bedrooms": PayloadSchemaType.INTEGER,
    "bathrooms": PayloadSchemaType.INTEGER,
    "price": PayloadSchemaType.FLOAT,
    "surface": PayloadSchemaType.FLOAT,
    "condition": PayloadSchemaType.KEYWORD,
    "currency": PayloadSchemaType.KEYWORD,
}

_UPSERT_BATCH_SIZE = 100


class QdrantManager:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        if url:
            self._client = AsyncQdrantClient(url=url, api_key=api_key)
        else:
            self._client = AsyncQdrantClient(host=host, port=port)

    @property
    def client(self) -> AsyncQdrantClient:
        return self._client

    async def ensure_collection(self, model: EmbeddingModel) -> None:
        collection_name = COLLECTION_NAMES[model]
        dimensions = EMBEDDING_DIMENSIONS[model]

        if not await self._client.collection_exists(collection_name):
            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimensions,
                    distance=Distance.COSINE,
                ),
            )

        for field_name, schema_type in PAYLOAD_INDEXES.items():
            await self._client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=schema_type,
            )

    async def ensure_all_collections(self) -> None:
        for model in EmbeddingModel:
            await self.ensure_collection(model)

    async def collection_info(self, model: EmbeddingModel) -> dict[str, object]:
        collection_name = COLLECTION_NAMES[model]
        try:
            info = await self._client.get_collection(collection_name)
            return {
                "name": collection_name,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status.value,
            }
        except Exception:
            return {
                "name": collection_name,
                "status": "not_found",
            }

    async def upsert_points(
        self, collection_name: str, points: list[PointStruct]
    ) -> int:
        """Upsert points in batches. Returns total points upserted."""
        total = 0
        for i in range(0, len(points), _UPSERT_BATCH_SIZE):
            batch = points[i : i + _UPSERT_BATCH_SIZE]
            await self._client.upsert(
                collection_name=collection_name,
                points=batch,
            )
            total += len(batch)
            if total % 1000 == 0 or total == len(points):
                logger.info("Upserted %d / %d points", total, len(points))
        return total

    async def close(self) -> None:
        await self._client.close()
