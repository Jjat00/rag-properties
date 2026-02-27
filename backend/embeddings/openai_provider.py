import asyncio
import logging

from openai import AsyncOpenAI

from config import EmbeddingModel
from embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)

_MODEL_IDS: dict[EmbeddingModel, str] = {
    EmbeddingModel.OPENAI_SMALL: "text-embedding-3-small",
    EmbeddingModel.OPENAI_LARGE: "text-embedding-3-large",
}

_BATCH_SIZE = 100
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: EmbeddingModel, api_key: str) -> None:
        super().__init__(model)
        self._client = AsyncOpenAI(api_key=api_key, timeout=60.0)
        self._model_id = _MODEL_IDS[model]

    async def _embed_with_retry(self, batch: list[str]) -> list[list[float]]:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self._client.embeddings.create(
                    input=batch,
                    model=self._model_id,
                )
                return [item.embedding for item in response.data]
            except Exception:
                if attempt == _MAX_RETRIES:
                    raise
                delay = _RETRY_DELAY * attempt
                logger.warning(
                    "OpenAI embed batch failed (attempt %d/%d), retrying in %.1fs",
                    attempt, _MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
        return []  # unreachable

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            embeddings = await self._embed_with_retry(batch)
            all_embeddings.extend(embeddings)
        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        response = await self._client.embeddings.create(
            input=[query],
            model=self._model_id,
        )
        return response.data[0].embedding
