from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingModel(str, Enum):
    OPENAI_SMALL = "openai-small"
    OPENAI_LARGE = "openai-large"
    GEMINI = "gemini"


EMBEDDING_DIMENSIONS: dict[EmbeddingModel, int] = {
    EmbeddingModel.OPENAI_SMALL: 1536,
    EmbeddingModel.OPENAI_LARGE: 3072,
    EmbeddingModel.GEMINI: 3072,
}

COLLECTION_NAMES: dict[EmbeddingModel, str] = {
    EmbeddingModel.OPENAI_SMALL: "properties_openai_small",
    EmbeddingModel.OPENAI_LARGE: "properties_openai_large",
    EmbeddingModel.GEMINI: "properties_gemini",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    gemini_api_key: str = ""
    default_embedding_model: EmbeddingModel = EmbeddingModel.GEMINI
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    excel_path: str = "data/properties.xlsx"
    search_top_k: int = 10
    query_parser_model: str = "gemini-3-flash-preview"
    agent_model: str = "gemini-2.5-flash"
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )


settings = Settings()
