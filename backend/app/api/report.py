"""Public read-only share view: /api/report/{token} → the saved result.

Only the token's SHA-256 hash is stored; expired links (report_ttl_days) return
404. No session id is exposed to the viewer.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment.read import result_payload
from app.db import get_session
from app.models import AssessmentSession, Report
from app.security.tokens import hash_token

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/{token}")
async def read_report(
    token: str, locale: str = "ru", session: AsyncSession = Depends(get_session)
) -> dict:
    # kind guard: a parent token must NEVER resolve to the full result — the
    # parent report deliberately hides raw buckets / llm_reason, and swapping
    # /p/<token> for /r/<token> would bypass that boundary otherwise.
    report = (
        await session.execute(
            select(Report).where(
                Report.token_hash == hash_token(token), Report.kind != "parent"
            )
        )
    ).scalars().first()
    if report is None or report.expires_at < dt.datetime.now(dt.UTC):
        raise HTTPException(status_code=404, detail="not found")
    ses = (
        await session.execute(
            select(AssessmentSession).where(AssessmentSession.id == report.session_id)
        )
    ).scalars().first()
    if ses is None:
        raise HTTPException(status_code=404, detail="not found")
    payload = await result_payload(session, ses, locale)
    if payload is None:
        raise HTTPException(status_code=404, detail="not found")
    payload["shared"] = True
    return payload
