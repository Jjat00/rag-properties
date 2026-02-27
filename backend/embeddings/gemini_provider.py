from google import genai

from config import EmbeddingModel
from embeddings.base import EmbeddingProvider

_MODEL_ID = "text-embedding-004"
_BATCH_SIZE = 100


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str) -> None:
        super().__init__(EmbeddingModel.GEMINI)
        self._client = genai.Client(api_key=api_key)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            result = self._client.models.embed_content(
                model=_MODEL_ID,
                contents=batch,
                config={
                    "task_type": "RETRIEVAL_DOCUMENT",
                },
            )
            all_embeddings.extend([list(e.values) for e in result.embeddings])
        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        result = self._client.models.embed_content(
            model=_MODEL_ID,
            contents=[query],
            config={
                "task_type": "RETRIEVAL_QUERY",
            },
        )
        return list(result.embeddings[0].values)
