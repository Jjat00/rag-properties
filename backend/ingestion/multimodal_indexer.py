"""Generate fused text+image embeddings and index multimodal properties into Qdrant.

Strategy: ONE point per property with a single fused embedding that combines
the text description + up to 6 images into one vector. Since gemini-embedding-2
maps all modalities into the same 3072d vector space, the fused embedding
captures both textual and visual semantics.

Properties without downloaded images get a text-only embedding.
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
    """Generate fused embeddings and upsert into Qdrant.

    For each property:
    - If images are available: creates a fused embedding (text + images → 1 vector)
    - If no images: creates a text-only embedding

    Returns the total number of points indexed (1 per property).
    """
    valid: list[MultimodalProperty] = [p for p in properties if p.id and p.embedding_text.strip()]
    skipped = len(properties) - len(valid)
    if skipped:
        logger.warning("Skipped %d properties (no ID or empty text)", skipped)

    if not valid:
        logger.warning("No valid properties to index")
        return 0

    # Separate properties with and without images
    with_images: list[tuple[MultimodalProperty, list[Path]]] = []
    without_images: list[MultimodalProperty] = []

    for prop in valid:
        paths = image_map.get(prop.id, [])
        if paths:
            with_images.append((prop, paths))
        else:
            without_images.append(prop)

    logger.info(
        "%d properties with images, %d text-only",
        len(with_images), len(without_images),
    )

    points: list[PointStruct] = []

    # Batch text-only embeddings (fast — one API call for all)
    if without_images:
        logger.info("Generating text embeddings for %d properties without images", len(without_images))
        texts = [p.embedding_text for p in without_images]
        text_embeddings = await provider.embed_texts(texts)

        for prop, emb in zip(without_images, text_embeddings):
            point_id = _id_to_uuid(prop.id)
            payload = prop.to_qdrant_payload()
            points.append(
                PointStruct(id=point_id, vector=emb, payload=payload)
            )

    # Fused embeddings (one API call per property — text + images combined)
    if with_images:
        logger.info("Generating fused embeddings for %d properties with images", len(with_images))
        for i, (prop, paths) in enumerate(with_images):
            try:
                fused_emb = await provider.embed_fused(prop.embedding_text, paths)
            except Exception:
                logger.warning("Failed to embed fused for %s, falling back to text-only", prop.id, exc_info=True)
                text_embs = await provider.embed_texts([prop.embedding_text])
                fused_emb = text_embs[0]

            point_id = _id_to_uuid(prop.id)
            payload = prop.to_qdrant_payload()
            points.append(
                PointStruct(id=point_id, vector=fused_emb, payload=payload)
            )

            if (i + 1) % 50 == 0:
                logger.info("Fused embeddings: %d / %d", i + 1, len(with_images))

    logger.info("Built %d points (1 per property)", len(points))
    logger.info("Upserting %d points into %s", len(points), MULTIMODAL_COLLECTION)
    total = await qdrant_manager.upsert_points(MULTIMODAL_COLLECTION, points)
    logger.info("Indexed %d multimodal points", total)
    return total
