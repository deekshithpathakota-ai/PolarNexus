"""Application settings, loaded from environment variables (see .env.example)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    APP_NAME: str = "PolarNexus"
    ENVIRONMENT: str = "development"

    # Database: PostgreSQL (+pgvector) recommended. Falls back to SQLite for quick local runs.
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'polarnexus.db'}"

    # Auth
    JWT_SECRET: str = "dev-only-change-me"
    JWT_EXPIRE_MINUTES: int = 60 * 12
    DEMO_MODE: bool = True  # enables one-click demo accounts + auto-seed on empty DB
    DEMO_USER_PASSWORD: str = "polarnexus-demo"

    # CORS — comma separated list of allowed frontend origins
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # AI provider (OpenAI or any OpenAI-compatible endpoint). Optional.
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_TIMEOUT_SECONDS: float = 30.0

    # Storage (local disk by default; S3/Supabase-compatible keys documented for production)
    STORAGE_DIR: str = str(BASE_DIR / "storage")
    STORAGE_URL: str = ""
    STORAGE_KEY: str = ""
    STORAGE_SECRET: str = ""
    MAX_UPLOAD_MB: int = 25

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgres")

    @property
    def sqlalchemy_url(self) -> str:
        url = self.DATABASE_URL
        # Managed providers often hand out postgres:// URLs; SQLAlchemy + psycopg3 needs this form.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def llm_enabled(self) -> bool:
        return bool(self.OPENAI_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
