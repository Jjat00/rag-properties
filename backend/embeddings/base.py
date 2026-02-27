from abc import ABC, abstractmethod

from config import EmbeddingModel, COLLECTION_NAMES, EMBEDDING_DIMENSIONS


class EmbeddingProvider(ABC):
    def __init__(self, model: EmbeddingModel) -> None:
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model.value

    @property
    def dimensions(self) -> int:
        return EMBEDDING_DIMENSIONS[self._model]

    @property
    def collection_name(self) -> str:
        return COLLECTION_NAMES[self._model]

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts (documents)."""
        ...

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single search query."""
        ...
