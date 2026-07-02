"""Public metadata: methodology honesty banner + active scoring config version.

The 'methodology_stage' string is surfaced in the UI so results are always
framed as an early product adaptation of the RIASEC model — never 'validated'
(METHOD.md).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import ScoringConfig

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("")
async def meta(session: AsyncSession = Depends(get_session)) -> dict:
    latest = (
        await session.execute(select(ScoringConfig).order_by(ScoringConfig.version.desc()))
    ).scalars().first()
    return {
        "methodology": "riasec-based",  # not "validated" — see METHOD.md
        "methodology_stage": "early",
        "scoring_version": latest.version if latest else None,
    }
