"""Async SQLAlchemy engine, session factory, declarative Base, and FastAPI dependency."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
engine_kwargs: dict[str, Any] = {"echo": settings.DEBUG}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Declarative Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Common declarative base for all ORM models."""

    type_annotation_map: dict[Any, Any] = {}


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, commit on success, rollback on exception, and ensure closed."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Create all ORM-mapped tables (dev convenience; use Alembic in production)."""
    # Import here to ensure all models are registered before metadata.create_all
    import app.models.all  # noqa: F401
    import app.models.batch  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created / verified.")
    except Exception as exc:
        logger.warning(f"Database table verification deferred/warning: {exc}")
