from config import EmbeddingModel, Settings
from embeddings.base import EmbeddingProvider
from embeddings.gemini_provider import GeminiEmbeddingProvider
from embeddings.openai_provider import OpenAIEmbeddingProvider


class EmbeddingRegistry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: dict[EmbeddingModel, EmbeddingProvider] = {}

    def get(self, model: EmbeddingModel) -> EmbeddingProvider:
        if model in self._cache:
            return self._cache[model]

        provider: EmbeddingProvider
        if model in (EmbeddingModel.OPENAI_SMALL, EmbeddingModel.OPENAI_LARGE):
            provider = OpenAIEmbeddingProvider(
                model=model,
                api_key=self._settings.openai_api_key,
            )
        elif model == EmbeddingModel.GEMINI:
            provider = GeminiEmbeddingProvider(
                api_key=self._settings.gemini_api_key,
            )
        else:
            raise ValueError(f"Unknown embedding model: {model}")

        self._cache[model] = provider
        return provider

    def get_default(self) -> EmbeddingProvider:
        return self.get(self._settings.default_embedding_model)

    def get_all(self) -> list[EmbeddingProvider]:
        return [self.get(model) for model in EmbeddingModel]
