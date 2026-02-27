import asyncio
from functools import partial

from google import genai

from config import EmbeddingModel
from embeddings.base import EmbeddingProvider

_MODEL_ID = "gemini-embedding-001"
_BATCH_SIZE = 100


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(EmbeddingModel.GEMINI)
        self._client = genai.Client(api_key=api_key)

    def _embed_sync(self, contents: list[str], task_type: str) -> list[list[float]]:
        result = self._client.models.embed_content(
            model=_MODEL_ID,
            contents=contents,
            config={"task_type": task_type},
        )
        return [list(e.values) for e in result.embeddings]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            embeddings = await asyncio.to_thread(
                partial(self._embed_sync, batch, "RETRIEVAL_DOCUMENT")
            )
            all_embeddings.extend(embeddings)
        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        embeddings = await asyncio.to_thread(
            partial(self._embed_sync, [query], "RETRIEVAL_QUERY")
        )
        return embeddings[0]
