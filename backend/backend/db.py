"""Async SQLAlchemy engine, session factory and declarative base."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def build_engine(settings: Settings | None = None) -> AsyncEngine:
    """Build an ``AsyncEngine`` from settings."""
    cfg = settings or get_settings()
    kwargs: dict[str, object] = {"future": True, "echo": False}
    if cfg.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_async_engine(cfg.database_url, **kwargs)


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build an ``async_sessionmaker`` bound to an engine."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, building it on first use."""
    global _engine
    if _engine is None:
        _engine = build_engine()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide sessionmaker."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = build_sessionmaker(get_engine())
    return _sessionmaker


def set_sessionmaker(maker: async_sessionmaker[AsyncSession]) -> None:
    """Override the sessionmaker (used by tests / lifespan)."""
    global _sessionmaker
    _sessionmaker = maker


def set_engine(engine: AsyncEngine) -> None:
    """Override the engine (used by tests / lifespan)."""
    global _engine
    _engine = engine


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an ``AsyncSession``."""
    maker = get_sessionmaker()
    async with maker() as session:
        yield session
