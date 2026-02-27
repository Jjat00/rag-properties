"""Generate embeddings and index properties into Qdrant."""

import logging
import uuid

from qdrant_client.models import PointStruct

from embeddings.base import EmbeddingProvider
from models.property import Property
from vectorstore.qdrant_manager import QdrantManager

logger = logging.getLogger(__name__)


def _id_to_uuid(hex_id: str) -> str:
    """Convert a hex string ID to a deterministic UUID for Qdrant.

    Uses UUID5 with a fixed namespace so the same property ID always
    maps to the same Qdrant point ID (idempotent upserts).
    """
    namespace = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    return str(uuid.uuid5(namespace, hex_id))


async def index_properties(
    properties: list[Property],
    provider: EmbeddingProvider,
    qdrant_manager: QdrantManager,
) -> int:
    """Generate embeddings and upsert properties into Qdrant.

    Returns the number of points indexed.
    """
    # Filter properties with non-empty embedding text and valid IDs
    valid: list[tuple[Property, str]] = []
    for prop in properties:
        if not prop.id:
            continue
        text = prop.embedding_text.strip()
        if not text:
            continue
        valid.append((prop, text))

    skipped = len(properties) - len(valid)
    if skipped:
        logger.warning("Skipped %d properties (no ID or empty embedding text)", skipped)

    if not valid:
        logger.warning("No valid properties to index")
        return 0

    logger.info(
        "Generating embeddings for %d properties with %s",
        len(valid),
        provider.model_name,
    )

    texts = [text for _, text in valid]
    embeddings = await provider.embed_texts(texts)

    logger.info("Building Qdrant points")
    points: list[PointStruct] = []
    for (prop, _), embedding in zip(valid, embeddings):
        point_id = _id_to_uuid(prop.id)  # type: ignore[arg-type]
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload=prop.to_qdrant_payload(),
            )
        )

    collection_name = provider.collection_name
    logger.info("Upserting %d points into %s", len(points), collection_name)
    total = await qdrant_manager.upsert_points(collection_name, points)

    logger.info("Indexed %d points into %s", total, collection_name)
    return total
