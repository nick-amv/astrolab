"""Authenticated account surface: the user's saved results + self-service
deletion (PRIVACY_MODEL §4/§8 — the erasure path is wired to the account here)."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import (
    AssessmentSession,
    DeletionLog,
    Match,
    Occupation,
    OccupationI18n,
    PlanItem,
    Profile,
    User,
)
from app.security.session import clear_session_cookie, require_user
from app.services.next_steps import resolve_steps

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


class PlanToggleIn(BaseModel):
    slug: str
    step_idx: int
    audience: str = "adult"


@router.post("/plan/toggle")
async def toggle_plan_step(
    body: PlanToggleIn,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Check/uncheck one 'try it this week' step (N4). First click on a step both
    saves the plan for that occupation and marks the step done; a re-click flips
    `done`. step_idx must be one of the 4 curated steps (0..3)."""
    if body.audience not in ("teen", "adult") or not 0 <= body.step_idx <= 3:
        raise HTTPException(status_code=422, detail="bad step")
    row = (
        await session.execute(
            select(PlanItem).where(
                PlanItem.user_id == user.id,
                PlanItem.occupation_slug == body.slug,
                PlanItem.step_idx == body.step_idx,
            )
        )
    ).scalars().first()
    if row is None:
        row = PlanItem(
            user_id=user.id,
            occupation_slug=body.slug,
            step_idx=body.step_idx,
            audience=body.audience,
            done=True,
        )
        session.add(row)
    else:
        row.done = not row.done
    await session.commit()
    return {"done": row.done}


@router.get("/plan")
async def my_plan(
    locale: str = "ru",
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """The user's saved plans grouped by occupation, each with resolved step text
    + link + done state, so the account page renders without the frontend
    knowing the step catalogue."""
    items = (
        await session.execute(
            select(PlanItem)
            .where(PlanItem.user_id == user.id)
            .order_by(PlanItem.occupation_slug, PlanItem.step_idx)
        )
    ).scalars().all()
    if not items:
        return {"plans": []}

    slugs = list({it.occupation_slug for it in items})
    occs = (
        await session.execute(select(Occupation).where(Occupation.slug.in_(slugs)))
    ).scalars().all()
    field_by = {o.slug: o.field_tag for o in occs}
    id_by_slug = {o.id: o.slug for o in occs}
    titles = (
        await session.execute(
            select(OccupationI18n).where(
                OccupationI18n.occupation_id.in_([o.id for o in occs])
            )
        )
    ).scalars().all()
    title_by: dict[tuple[str, str], str] = {
        (id_by_slug[r.occupation_id], r.locale): r.title
        for r in titles
        if r.occupation_id in id_by_slug
    }

    plans: list[dict] = []
    for slug in slugs:
        rows = [it for it in items if it.occupation_slug == slug]
        title = title_by.get((slug, locale)) or title_by.get((slug, "ru")) or slug
        audience = rows[0].audience
        done_by = {it.step_idx: it.done for it in rows}
        steps = [
            {**s, "done": done_by.get(s["idx"], False)}
            for s in resolve_steps(field_by.get(slug), audience, locale, title)
            if s["idx"] in done_by
        ]
        plans.append({"slug": slug, "title": title, "audience": audience, "steps": steps})
    return {"plans": plans}


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
