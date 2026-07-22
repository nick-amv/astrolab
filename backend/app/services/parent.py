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
    loc = locale if locale in ("ru", "en", "es", "fr", "de") else "ru"
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
    by = {(str(r.occupation_id), r.locale): r for r in i18n}

    # 'why' MUST be curated catalog copy, never Match.llm_reason: the rerank
    # reason is shaped by the teen's private mini-interview / CV answers, so
    # surfacing it to a parent would leak derived personal content and break the
    # 'no raw answers' boundary this report promises. who_fits / summary are
    # generic, reviewed content that is safe to share.
    professions = []
    for m, slug in rows:
        row = by.get((str(m.occupation_id), locale)) or by.get((str(m.occupation_id), "ru"))
        professions.append(
            {
                "slug": slug,
                "title": row.title if row else slug,
                "why": (row.who_fits or row.summary) if row else None,
            }
        )
    return {"axes": axes, "strengths": strengths, "support": support, "professions": professions}
