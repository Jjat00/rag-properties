"""Generate text + image embeddings and index multimodal properties into Qdrant."""

import logging
import uuid
from pathlib import Path

from qdrant_client.models import PointStruct

from config import MULTIMODAL_COLLECTION
from embeddings.gemini_multimodal_provider import GeminiMultimodalProvider
from models.multimodal_property import MultimodalProperty
from vectorstore.qdrant_manager import QdrantManager

logger = logging.getLogger(__name__)

_NAMESPACE = uuid.UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901")


def _id_to_uuid(doc_id: str) -> str:
    """Deterministic UUID from document ID for idempotent upserts."""
    return str(uuid.uuid5(_NAMESPACE, doc_id))


async def index_multimodal_properties(
    properties: list[MultimodalProperty],
    image_map: dict[str, list[Path]],
    provider: GeminiMultimodalProvider,
    qdrant_manager: QdrantManager,
) -> int:
    """Generate text + image embeddings and upsert into Qdrant.

    Returns the number of points indexed.
    """
    valid: list[MultimodalProperty] = [p for p in properties if p.id and p.embedding_text.strip()]
    skipped = len(properties) - len(valid)
    if skipped:
        logger.warning("Skipped %d properties (no ID or empty text)", skipped)

    if not valid:
        logger.warning("No valid properties to index")
        return 0

    # Generate text embeddings in batch
    logger.info("Generating text embeddings for %d properties", len(valid))
    texts = [p.embedding_text for p in valid]
    text_embeddings = await provider.embed_texts(texts)

    # Generate image embeddings one property at a time
    logger.info("Generating image embeddings...")
    image_embeddings: list[list[float] | None] = []
    for prop in valid:
        paths = image_map.get(prop.id, [])
        if paths:
            try:
                img_emb = await provider.embed_images(paths)
                image_embeddings.append(img_emb)
            except Exception:
                logger.warning("Failed to embed images for %s", prop.id, exc_info=True)
                image_embeddings.append(None)
        else:
            image_embeddings.append(None)

    # Build points with named vectors
    logger.info("Building Qdrant points with named vectors")
    points: list[PointStruct] = []
    for prop, text_emb, img_emb in zip(valid, text_embeddings, image_embeddings):
        point_id = _id_to_uuid(prop.id)
        vectors: dict[str, list[float]] = {"text": text_emb}
        if img_emb:
            vectors["image"] = img_emb
        points.append(
            PointStruct(
                id=point_id,
                vector=vectors,
                payload=prop.to_qdrant_payload(),
            )
        )

    logger.info("Upserting %d points into %s", len(points), MULTIMODAL_COLLECTION)
    total = await qdrant_manager.upsert_points(MULTIMODAL_COLLECTION, points)
    logger.info("Indexed %d multimodal points", total)
    return total
