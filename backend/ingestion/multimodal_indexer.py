"""Generate text + image embeddings and index multimodal properties into Qdrant.

Strategy: one point per image + one text point per property.
Each image gets its own point with an individual embedding (no averaging),
so search matches against specific images (facade, kitchen, etc.) instead
of a blurred average. Deduplication happens at search time.
"""

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

    Creates one text point per property + one image point per individual image.
    Returns the total number of points indexed.
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

    # Build text points (1 per property)
    points: list[PointStruct] = []
    for prop, text_emb in zip(valid, text_embeddings):
        point_id = _id_to_uuid(prop.id)
        payload = prop.to_qdrant_payload()
        payload["point_type"] = "text"
        points.append(
            PointStruct(
                id=point_id,
                vector={"text": text_emb},
                payload=payload,
            )
        )

    # Generate image embeddings individually (1 vector per image, no averaging)
    logger.info("Generating individual image embeddings...")
    for prop in valid:
        paths = image_map.get(prop.id, [])
        if not paths:
            continue
        try:
            image_vectors = await provider.embed_images_individually(paths)
        except Exception:
            logger.warning("Failed to embed images for %s", prop.id, exc_info=True)
            continue

        for img_idx, (img_path, img_vec) in enumerate(zip(paths, image_vectors)):
            img_point_id = _id_to_uuid(f"{prop.id}_img_{img_idx}")
            payload = prop.to_qdrant_payload()
            payload["point_type"] = "image"
            payload["image_index"] = img_idx
            payload["image_url"] = prop.pictures[img_idx] if img_idx < len(prop.pictures) else None
            points.append(
                PointStruct(
                    id=img_point_id,
                    vector={"image": img_vec},
                    payload=payload,
                )
            )

    text_count = sum(1 for p in points if p.payload.get("point_type") == "text")
    image_count = len(points) - text_count
    logger.info(
        "Built %d points (%d text + %d image) for %d properties",
        len(points), text_count, image_count, len(valid),
    )

    logger.info("Upserting %d points into %s", len(points), MULTIMODAL_COLLECTION)
    total = await qdrant_manager.upsert_points(MULTIMODAL_COLLECTION, points)
    logger.info("Indexed %d multimodal points", total)
    return total
