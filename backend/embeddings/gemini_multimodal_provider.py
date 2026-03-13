"""Gemini Embedding 2 multimodal provider (text + images)."""

import asyncio
import logging
from functools import partial
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_MODEL_ID = "gemini-embedding-2-preview"
_BATCH_SIZE = 100
_MAX_IMAGES_PER_REQUEST = 6


class GeminiMultimodalProvider:
    """Embedding provider using gemini-embedding-2-preview for text and images.

    NOT a subclass of EmbeddingProvider — different interface (supports images).
    """

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    def _embed_text_sync(self, contents: list[str], task_type: str) -> list[list[float]]:
        result = self._client.models.embed_content(
            model=_MODEL_ID,
            contents=contents,
            config={"task_type": task_type},
        )
        return [list(e.values) for e in result.embeddings]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch text embeddings for document indexing."""
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            embeddings = await asyncio.to_thread(
                partial(self._embed_text_sync, batch, "RETRIEVAL_DOCUMENT")
            )
            all_embeddings.extend(embeddings)
        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        """Single query embedding for search."""
        embeddings = await asyncio.to_thread(
            partial(self._embed_text_sync, [query], "RETRIEVAL_QUERY")
        )
        return embeddings[0]

    def _embed_images_sync(self, image_paths: list[Path]) -> list[float]:
        """Read images from disk and create a single aggregated embedding.

        Sends up to 6 images in one request. Returns the embedding of the combined content.
        """
        paths = image_paths[:_MAX_IMAGES_PER_REQUEST]
        parts: list[types.Part] = []
        for path in paths:
            image_bytes = path.read_bytes()
            parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            )

        result = self._client.models.embed_content(
            model=_MODEL_ID,
            contents=parts,
            config={"task_type": "RETRIEVAL_DOCUMENT"},
        )
        # Average the per-image embeddings into one vector
        vectors = [list(e.values) for e in result.embeddings]
        if len(vectors) == 1:
            return vectors[0]
        dim = len(vectors[0])
        avg = [sum(v[d] for v in vectors) / len(vectors) for d in range(dim)]
        return avg

    async def embed_images(self, image_paths: list[Path]) -> list[float]:
        """Generate aggregated image embedding (up to 6 images -> 1 vector)."""
        if not image_paths:
            return []
        return await asyncio.to_thread(
            partial(self._embed_images_sync, image_paths)
        )

    def _embed_image_query_sync(self, image_bytes: bytes, mime_type: str) -> list[float]:
        """Embed a single image as a retrieval query (cross-modal search)."""
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        result = self._client.models.embed_content(
            model=_MODEL_ID,
            contents=[part],
            config={"task_type": "RETRIEVAL_QUERY"},
        )
        return list(result.embeddings[0].values)

    async def embed_image_query(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> list[float]:
        """Embed an uploaded image for cross-modal search against text and image vectors."""
        return await asyncio.to_thread(
            partial(self._embed_image_query_sync, image_bytes, mime_type)
        )
