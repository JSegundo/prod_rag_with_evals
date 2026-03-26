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
    llm_model: str = "claude-sonnet-4-20250514"
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 1536

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
