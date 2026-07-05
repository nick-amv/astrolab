"""Public parent view: /api/parent/{token} -> the warm, no-raw-answers report.

Only the token's SHA-256 hash is stored; only 'parent'-kind reports resolve here
(a normal share token 404s); expired links (report_ttl_days) return 404. No
session id and no raw answers are exposed to the viewer (N5)."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import AssessmentSession, Report
from app.security.tokens import hash_token
from app.services.parent import build_parent_view

router = APIRouter(prefix="/api/parent", tags=["parent"])


@router.get("/{token}")
async def read_parent(
    token: str, locale: str = "ru", session: AsyncSession = Depends(get_session)
) -> dict:
    report = (
        await session.execute(
            select(Report).where(
                Report.token_hash == hash_token(token), Report.kind == "parent"
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
    view = await build_parent_view(session, ses, locale)
    if view is None:
        raise HTTPException(status_code=404, detail="not found")
    return view
