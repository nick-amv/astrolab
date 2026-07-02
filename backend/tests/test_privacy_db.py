"""DB-backed acceptance tests (CI only): the schema migrates from zero, the
scoring_config immutability trigger fires, and the deletion path erases an
anonymous profile. These exercise the Wave 0 gates end to end."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from app.config import settings
from app.services.retention import purge_anonymous_sessions
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.conftest import requires_db

pytestmark = requires_db


def _engine():
    return create_async_engine(settings.database_url, poolclass=None)


async def test_scoring_config_is_immutable() -> None:
    engine = _engine()
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as s:
        row = (await s.execute(text("SELECT version FROM scoring_config ORDER BY version"))).first()
        assert row is not None, "scoring_config must be seeded with v1"
        with pytest.raises(DBAPIError):  # trigger rejects UPDATE
            await s.execute(text("UPDATE scoring_config SET note='x' WHERE version=1"))
            await s.commit()
    await engine.dispose()


async def test_anonymous_retention_purges_old_profiles() -> None:
    engine = _engine()
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    old_token = f"anon-{uuid.uuid4()}"
    async with Session() as s:
        # Insert an anonymous profile backdated beyond the retention window.
        await s.execute(
            text(
                "INSERT INTO profiles (id, anon_token, age_band, locale, created_at) "
                "VALUES (gen_random_uuid(), :t, '17-19', 'ru', now() - interval '200 days')"
            ),
            {"t": old_token},
        )
        await s.commit()
        now = dt.datetime.now(dt.UTC)
        purged = await purge_anonymous_sessions(s, now, settings.retention_days)
        assert purged >= 1
        remaining = (
            await s.execute(
                text("SELECT count(*) FROM profiles WHERE anon_token=:t"), {"t": old_token}
            )
        ).scalar()
        assert remaining == 0
    await engine.dispose()
