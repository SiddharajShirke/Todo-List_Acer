"""
config.py — Central Settings (pydantic-settings)
All configuration read from .env file with type validation.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Supabase ──────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # ── Database (PostgreSQL via Supabase Transaction Pooler) ─────────
    # Format: postgresql+psycopg2://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    DATABASE_URL: str = "sqlite:///./dev.db"

    # Connection Pool (PostgreSQL only)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800       # Recycle connections every 30 min

    # ── NVIDIA NIM LLM ────────────────────────────────────────────────
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "nvidia/llama-3.1-nemotron-70b-instruct"

    # ── Gemini LLM ────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""

    # ── Redis (Celery Broker) ─────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Google OAuth ──────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # ── App Config ────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:5500,http://localhost:5500,http://localhost:5173,http://localhost:5174"

    @property
    def cors_origins_list(self) -> list:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
