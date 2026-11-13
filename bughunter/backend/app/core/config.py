"""Application configuration via Pydantic Settings."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ────────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://bughunter:bughunter@db:5432/bughunter",
        description="Async PostgreSQL connection string",
    )
    # Sync URL used by Alembic (psycopg2)
    SYNC_DATABASE_URL: str = Field(
        default="postgresql+psycopg2://bughunter:bughunter@db:5432/bughunter",
        description="Sync PostgreSQL connection string for Alembic",
    )

    # ── Redis / Celery ───────────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL",
    )
    CELERY_BROKER_URL: str = Field(
        default="redis://redis:6379/1",
        description="Celery broker URL",
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://redis:6379/2",
        description="Celery result backend URL",
    )

    # ── Security ─────────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="b9f2d1e8c7a6b5e4d3c2b1a0f9e8d7c6b5a4938271605f4e3d2c1b0a9f8e7d6c",
        description="JWT signing secret — defaults to dev secret if missing from environment",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, description="JWT access token lifetime in minutes"
    )

    # ── AI Configuration ──────────────────────────────────────────────────────────
    AI_BASE_URL: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI-compatible API base URL (OpenAI, OpenRouter, Groq, Ollama, etc.)",
    )
    AI_API_KEY: str = Field(
        default="",
        description="API key for AI provider",
    )
    AI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Model identifier sent to AI provider",
    )

    # ── App ──────────────────────────────────────────────────────────────────────
    APP_NAME: str = Field(default="BugHunter AI", description="Application name")
    FRONTEND_ORIGIN: str = Field(default="http://localhost:3000", description="Frontend origin for CORS")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # ── Evidence / Report storage ────────────────────────────────────────────────
    EVIDENCE_DIR: str = Field(
        default="/data/evidence", description="Root directory for evidence files"
    )
    REPORT_DIR: str = Field(
        default="/data/reports", description="Root directory for report PDF files"
    )

    # ── Scan defaults ────────────────────────────────────────────────────────────
    DEFAULT_SCAN_TIMEOUT: int = Field(
        default=300, description="Default tool execution timeout in seconds"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()


settings = get_settings()
