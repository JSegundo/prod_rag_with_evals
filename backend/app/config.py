from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root (one level up from backend/)
_env_file = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://postgres:yourpassword@localhost:5438/ragdb"

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # App Config
    uploads_dir: str = str(Path(__file__).resolve().parent.parent.parent / "uploads")
    extractor: str = "pdfplumber"
    llm_provider: str = "anthropic"
    # Model IDs get retired by Anthropic over time (404 not_found_error) --
    # if this one dies, check client.models.list() for a replacement.
    llm_model: str = "claude-sonnet-5-5"
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 1536

    # RAG / Confidence
    # Note: text-embedding-3-large cosine scores are typically 0.2-0.5 for real queries.
    # These thresholds are calibrated for that range. Adjust via env vars if using a different model.
    similarity_threshold: float = 0.25
    confidence_high: float = 0.40
    confidence_medium: float = 0.30

    # Eval
    auto_eval_on_reindex: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
