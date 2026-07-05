"""N5 parent report: a warm, no-raw-answers view a teen can share with a parent.

Only for teen sessions (the age gate lives in the API). Content — axis labels,
strengths, and 'how to support, not push' tips — is curated per RIASEC axis in
seed/parent_tips.json; never LLM. The payload deliberately carries NO raw answers
and NO full match list: top-2 axes, ~4 strengths, 3 support tips, top-3
professions with 'why'."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AssessmentSession, Match, Occupation, OccupationI18n, TraitScore

_SEED = Path(__file__).resolve().parents[2] / "seed" / "parent_tips.json"
_AXES = ("R", "I", "A", "S", "E", "C")


@lru_cache(maxsize=1)
def _tips() -> dict:
    return json.loads(_SEED.read_text(encoding="utf-8"))


async def build_parent_view(
    session: AsyncSession, ses: AssessmentSession, locale: str
) -> dict | None:
    """Warm parent view, or None if the session isn't scored yet."""
    riasec_row = (
        await session.execute(
            select(TraitScore).where(
                TraitScore.session_id == ses.id, TraitScore.kind == "riasec"
            )
        )
    ).scalars().first()
    if riasec_row is None or not riasec_row.vector:
        return None
    tips = _tips()
    loc = "en" if locale == "en" else "ru"
    vec = riasec_row.vector
    top2 = sorted(_AXES, key=lambda a: vec.get(a, 0.0), reverse=True)[:2]

    axes = [{"axis": a, "label": tips[a][f"label_{loc}"]} for a in top2]
    strengths = list(tips[top2[0]][f"strengths_{loc}"]) + list(tips[top2[1]][f"strengths_{loc}"])
    support = list(tips[top2[0]][f"support_{loc}"])[:3]

    # top-3 professions by final display rank, title + 'why' (no scores, no bucket).
    rows = (
        await session.execute(
            select(Match, Occupation.slug)
            .join(Occupation, Occupation.id == Match.occupation_id)
            .where(Match.session_id == ses.id)
            .order_by(Match.rank_final)
            .limit(3)
        )
    ).all()
    occ_ids = [m.occupation_id for (m, _s) in rows]
    i18n = (
        await session.execute(
            select(OccupationI18n).where(OccupationI18n.occupation_id.in_(occ_ids))
        )
    ).scalars().all()
    t = {(str(r.occupation_id), r.locale): r.title for r in i18n}
    professions = [
        {
            "slug": slug,
            "title": t.get((str(m.occupation_id), locale))
            or t.get((str(m.occupation_id), "ru"))
            or slug,
            "why": m.llm_reason,
        }
        for m, slug in rows
    ]
    return {"axes": axes, "strengths": strengths, "support": support, "professions": professions}
