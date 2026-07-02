"""Data-retention purge (PRIVACY_MODEL.md, acceptance gate Wave 0).

Two jobs, both idempotent and safe to run repeatedly:
- purge_anonymous_sessions(): deletes anonymous profiles (no user_id) older
  than settings.retention_days. Cascades to sessions/answers/scores/matches/
  interviews/reports via FK ondelete=CASCADE.
- purge_expired_tokens(): removes expired auth tokens and expired share reports.

Wired to a systemd timer on nikam (deploy/systemd/astrolab-retention.*).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select

from app.models import AuthToken, Profile, Report


async def purge_anonymous_sessions(session, now: dt.datetime, retention_days: int) -> int:
    cutoff = now - dt.timedelta(days=retention_days)
    ids = (
        await session.execute(
            select(Profile.id).where(
                Profile.user_id.is_(None),
                Profile.created_at < cutoff,
            )
        )
    ).scalars().all()
    if not ids:
        return 0
    await session.execute(delete(Profile).where(Profile.id.in_(ids)))
    await session.commit()
    return len(ids)


async def purge_expired_tokens(session, now: dt.datetime) -> int:
    r1 = await session.execute(delete(AuthToken).where(AuthToken.expires_at < now))
    r2 = await session.execute(delete(Report).where(Report.expires_at < now))
    await session.commit()
    return (r1.rowcount or 0) + (r2.rowcount or 0)
