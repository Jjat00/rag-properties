from openai import AsyncOpenAI

from config import EmbeddingModel
from embeddings.base import EmbeddingProvider

_MODEL_IDS: dict[EmbeddingModel, str] = {
    EmbeddingModel.OPENAI_SMALL: "text-embedding-3-small",
    EmbeddingModel.OPENAI_LARGE: "text-embedding-3-large",
}

_BATCH_SIZE = 500


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: EmbeddingModel, api_key: str) -> None:
        super().__init__(model)
        self._client = AsyncOpenAI(api_key=api_key)
        self._model_id = _MODEL_IDS[model]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            response = await self._client.embeddings.create(
                input=batch,
                model=self._model_id,
            )
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        response = await self._client.embeddings.create(
            input=[query],
            model=self._model_id,
        )
        return response.data[0].embedding
