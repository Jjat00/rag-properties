from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    VectorParams,
)

from config import COLLECTION_NAMES, EMBEDDING_DIMENSIONS, EmbeddingModel

PAYLOAD_INDEXES: dict[str, PayloadSchemaType] = {
    "city": PayloadSchemaType.KEYWORD,
    "state": PayloadSchemaType.KEYWORD,
    "property_type": PayloadSchemaType.KEYWORD,
    "operation": PayloadSchemaType.KEYWORD,
    "bedrooms": PayloadSchemaType.INTEGER,
    "bathrooms": PayloadSchemaType.INTEGER,
    "price": PayloadSchemaType.FLOAT,
    "surface": PayloadSchemaType.FLOAT,
    "condition": PayloadSchemaType.KEYWORD,
}


class QdrantManager:
    def __init__(self, host: str, port: int) -> None:
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

    async def close(self) -> None:
        await self._client.close()
