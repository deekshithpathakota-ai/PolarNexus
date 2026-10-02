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
    # v3: provider-neutral names. LLM_* / EMBEDDING_* take precedence; the original OPENAI_* names keep working.
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_PROVIDER: str = ""          # "", "openai", "openai-compatible" (Groq, Together, vLLM, Ollama…) or "none"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_PROVIDER: str = ""    # "", "openai", "openai-compatible" or "local" (offline TF-IDF + LSA)
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_TIMEOUT_SECONDS: float = 30.0

    # Visual semantic search (text → image/video-frame retrieval in a shared CLIP embedding space).
    # "auto" enables it when the optional `fastembed` package is installed (requirements-visual.txt);
    # "clip" requires it; "none" disables it. Models are ONNX (no PyTorch) and are cached in VISUAL_MODEL_CACHE.
    VISUAL_SEARCH_PROVIDER: str = "auto"
    VISUAL_IMAGE_MODEL: str = "Qdrant/clip-ViT-B-32-vision"
    VISUAL_TEXT_MODEL: str = "Qdrant/clip-ViT-B-32-text"
    VISUAL_MODEL_CACHE: str = str(BASE_DIR / ".model_cache")
    VIDEO_MAX_KEYFRAMES: int = 24
    # Calibrated on the bundled photographs: unrelated queries score ~0.20–0.26 with CLIP ViT-B/32
    VISUAL_MIN_SIMILARITY: float = 0.265

    # OCR for scanned PDFs (tesseract CLI). Pages with too little extractable text are rendered and OCR'd.
    OCR_ENABLED: bool = True
    OCR_LANGUAGES: str = "eng"
    OCR_MIN_CHARS_PER_PAGE: int = 40
    OCR_MAX_PAGES: int = 60

    # Dataset ingestion (CSV / JSON)
    MAX_DATASET_MB: int = 25
    MAX_DATASET_ROWS: int = 100_000

    # Rate limiting for expensive endpoints (per client IP, per minute; 0 disables)
    RATE_LIMIT_AI_PER_MINUTE: int = 60
    RATE_LIMIT_UPLOADS_PER_MINUTE: int = 20

    # Session cookie (HttpOnly) issued alongside the bearer token. Bearer tokens keep working.
    AUTH_COOKIE_ENABLED: bool = True
    AUTH_COOKIE_NAME: str = "pn_session"

    # Storage (local disk by default; S3-compatible object storage when STORAGE_BACKEND=s3)
    STORAGE_BACKEND: str = "local"  # local | s3
    S3_BUCKET: str = ""
    S3_ENDPOINT_URL: str = ""
    S3_REGION: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_PREFIX: str = "polarnexus/"
    STORAGE_DIR: str = str(BASE_DIR / "storage")
    STORAGE_URL: str = ""
    STORAGE_KEY: str = ""
    STORAGE_SECRET: str = ""
    MAX_UPLOAD_MB: int = 25
    # Media ingestion limits (images are decoded with Pillow; video metadata/thumbnails use ffmpeg when installed)
    MAX_IMAGE_MB: int = 20
    MAX_VIDEO_MB: int = 200
    MAX_IMAGE_PIXELS: int = 60_000_000  # decompression-bomb guard
    # Optional speech-to-text (OpenAI-compatible /audio/transcriptions). Uses OPENAI_API_KEY when set.
    STT_MODEL: str = "whisper-1"
    STT_ENABLED: bool = True

    # CORS: allow *.vercel.app preview deployments (convenient for the hackathon; disable for production)
    CORS_ALLOW_VERCEL_PREVIEWS: bool = True

    # Login throttling (per client IP + email, in-memory)
    LOGIN_MAX_FAILURES: int = 10
    LOGIN_WINDOW_SECONDS: int = 300

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

    # ---- provider resolution (new LLM_* / EMBEDDING_* names first, then the original OPENAI_* names)
    @property
    def llm_api_key(self) -> str:
        return self.LLM_API_KEY or self.OPENAI_API_KEY

    @property
    def llm_base_url(self) -> str:
        return (self.LLM_BASE_URL or self.OPENAI_BASE_URL).rstrip("/")

    @property
    def llm_enabled(self) -> bool:
        return self.LLM_PROVIDER.lower() != "none" and bool(self.llm_api_key)

    @property
    def embedding_api_key(self) -> str:
        return self.EMBEDDING_API_KEY or self.LLM_API_KEY or self.OPENAI_API_KEY

    @property
    def embedding_base_url(self) -> str:
        return (self.EMBEDDING_BASE_URL or self.LLM_BASE_URL or self.OPENAI_BASE_URL).rstrip("/")

    @property
    def embedding_api_enabled(self) -> bool:
        """Neural embeddings via an API. Unchanged default: on whenever a key is configured."""
        if self.EMBEDDING_PROVIDER.lower() in {"local", "none", "lsa"}:
            return False
        return bool(self.embedding_api_key)

    @property
    def stt_enabled(self) -> bool:
        return bool(self.llm_api_key) and self.STT_ENABLED

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
