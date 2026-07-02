"""Async database engine + session factory.

The app talks to Postgres via psycopg3 in async mode. Alembic uses the same
URL in sync mode (see alembic/env.py) — one driver, no drift.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields one session per request, always closed."""
    async with SessionLocal() as session:
        yield session
