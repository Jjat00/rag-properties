"""Gemini Embedding 2 multimodal provider (text + images).

All modalities (text, images) share the same 3072d vector space,
so a text query can find matching images and vice-versa using cosine similarity.
"""

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

    Key design: all modalities produce vectors in the SAME semantic space.
    A fused embedding (text + images combined) captures richer semantics
    than either modality alone.
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

    def _embed_fused_sync(self, text: str, image_paths: list[Path]) -> list[float]:
        """Create a single fused embedding from text + images.

        Combines text and up to 6 images into one Content with multiple Parts,
        producing ONE unified embedding that captures both textual description
        and visual appearance.
        """
        parts: list[types.Part] = [types.Part.from_text(text=text)]
        for path in image_paths[:_MAX_IMAGES_PER_REQUEST]:
            image_bytes = path.read_bytes()
            mime_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

        result = self._client.models.embed_content(
            model=_MODEL_ID,
            contents=[types.Content(parts=parts)],
            config={"task_type": "RETRIEVAL_DOCUMENT"},
        )
        return list(result.embeddings[0].values)

    async def embed_fused(self, text: str, image_paths: list[Path]) -> list[float]:
        """Create a fused embedding from text + images (one vector per property)."""
        return await asyncio.to_thread(
            partial(self._embed_fused_sync, text, image_paths)
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
        """Embed an uploaded image for cross-modal search."""
        return await asyncio.to_thread(
            partial(self._embed_image_query_sync, image_bytes, mime_type)
        )
