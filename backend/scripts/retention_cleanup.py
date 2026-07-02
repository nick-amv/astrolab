"""Retention purge entry point — run by a systemd timer on nikam (daily).

    python -m scripts.retention_cleanup

Deletes anonymous profiles past the retention window and expired tokens/reports.
Idempotent; safe to run repeatedly.
"""

from __future__ import annotations

import asyncio
import datetime as dt

from app.config import settings
from app.db import SessionLocal
from app.services.retention import purge_anonymous_sessions, purge_expired_tokens


async def main() -> None:
    now = dt.datetime.now(dt.UTC)
    async with SessionLocal() as session:
        purged = await purge_anonymous_sessions(session, now, settings.retention_days)
        tokens = await purge_expired_tokens(session, now)
    print(f"[retention] purged_profiles={purged} purged_tokens_reports={tokens}")


if __name__ == "__main__":
    asyncio.run(main())
