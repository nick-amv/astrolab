"""Authenticated account surface: the user's saved results + self-service
deletion (PRIVACY_MODEL §4/§8 — the erasure path is wired to the account here)."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import (
    AssessmentSession,
    DeletionLog,
    Match,
    OccupationI18n,
    Profile,
    User,
)
from app.security.session import clear_session_cookie, require_user

router = APIRouter(prefix="/api/me", tags=["account"])


@router.get("/results")
async def my_results(
    locale: str = "ru",
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List the user's completed assessments, newest first, each with the top few
    'core' occupation titles so the account page is meaningful at a glance."""
    profiles = (
        await session.execute(select(Profile).where(Profile.user_id == user.id))
    ).scalars().all()
    pid_band = {p.id: p.age_band for p in profiles}
    if not profiles:
        return {"results": []}

    sessions = (
        await session.execute(
            select(AssessmentSession)
            .where(
                AssessmentSession.profile_id.in_(list(pid_band)),
                AssessmentSession.status == "completed",
            )
            .order_by(AssessmentSession.finished_at.desc())
        )
    ).scalars().all()

    results = []
    for ses in sessions:
        titles = (
            await session.execute(
                select(OccupationI18n.title)
                .join(Match, Match.occupation_id == OccupationI18n.occupation_id)
                .where(
                    Match.session_id == ses.id,
                    Match.bucket == "core",
                    OccupationI18n.locale == locale,
                )
                .order_by(Match.rank_final)
                .limit(3)
            )
        ).scalars().all()
        results.append(
            {
                "session_id": str(ses.id),
                "finished_at": ses.finished_at.isoformat() if ses.finished_at else None,
                "age_band": pid_band.get(ses.profile_id),
                "top": list(titles),
            }
        )
    return {"results": results}


@router.post("/delete")
async def delete_me(
    response: Response,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete the account and everything linked to it (cascades to profiles,
    sessions, answers, results, tokens). Recorded in deletion_log."""
    now = dt.datetime.now(dt.UTC)
    session.add(DeletionLog(subject_ref=str(user.id), requested_at=now, completed_at=now))
    await session.execute(delete(User).where(User.id == user.id))
    await session.commit()
    clear_session_cookie(response)
    return {"ok": True}
