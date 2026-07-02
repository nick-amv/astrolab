"""Build the read-only result payload (profile + buckets with why-you) from
stored trait_scores + matches. Shared by the session result endpoint and the
public /r/<token> share view."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AssessmentSession,
    Match,
    Occupation,
    OccupationI18n,
    TraitScore,
)
from app.models import Profile as ProfileRow


async def _buckets(session: AsyncSession, session_id: uuid.UUID, locale: str) -> dict[str, list]:
    rows = (
        await session.execute(
            select(Match, Occupation.slug)
            .join(Occupation, Occupation.id == Match.occupation_id)
            .where(Match.session_id == session_id)
            .order_by(Match.rank_final)
        )
    ).all()
    out: dict[str, list] = {"core": [], "near": [], "dark_horse": []}
    if not rows:
        return out
    occ_ids = [m.occupation_id for (m, _s) in rows]
    i18n = (
        await session.execute(
            select(OccupationI18n).where(OccupationI18n.occupation_id.in_(occ_ids))
        )
    ).scalars().all()
    t = {(str(r.occupation_id), r.locale): r.title for r in i18n}
    for m, slug in rows:
        if m.bucket not in out:
            continue
        title = t.get((str(m.occupation_id), locale)) or t.get((str(m.occupation_id), "ru")) or slug
        out[m.bucket].append(
            {"slug": slug, "title": title, "score": round(m.score, 3), "why": m.llm_reason}
        )
    return out


async def result_payload(
    session: AsyncSession, ses: AssessmentSession, locale: str
) -> dict | None:
    """Full result, or None if the session hasn't been scored yet."""
    traits = (
        await session.execute(select(TraitScore).where(TraitScore.session_id == ses.id))
    ).scalars().all()
    by_kind = {t.kind: t.vector for t in traits}
    if not by_kind:
        return None
    profile_row = (
        await session.execute(select(ProfileRow).where(ProfileRow.id == ses.profile_id))
    ).scalars().first()
    return {
        "profile": {
            "riasec": by_kind.get("riasec", {}),
            "klimov": by_kind.get("klimov", {}),
            "values": by_kind.get("values", {}),
            "subjects": by_kind.get("subjects", {}),
        },
        "age_band": profile_row.age_band if profile_row else None,
        "buckets": await _buckets(session, ses.id, locale),
    }
