"""Apply multi-model review verdicts (DATA_SOURCES §6).

The review panel is run by the operator
and its per-model votes are captured in a verdicts JSON. This module records
those verdicts in `content_reviews` and publishes only occupations the council
approved. A 'split' or 'rejected' verdict leaves the occupation unpublished with
the disagreement retained for a follow-up pass.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.schema import ReviewVerdict
from app.models import ContentReview, Occupation, OccupationI18n


async def apply_verdict(session: AsyncSession, verdict: ReviewVerdict) -> str:
    """Record the council verdict; publish iff approved. Returns a status string."""
    occ = (
        await session.execute(select(Occupation).where(Occupation.slug == verdict.slug))
    ).scalars().first()
    if occ is None:
        return f"skip: no occupation '{verdict.slug}'"

    session.add(
        ContentReview(
            occupation_id=occ.id,
            locale=verdict.locale,
            verdict=verdict.verdict,
            models=[m.model_dump() for m in verdict.models],
            factual_flags=list(verdict.factual_flags) or None,
        )
    )

    if verdict.verdict == "approved" and not verdict.factual_flags:
        i18n = (
            await session.execute(
                select(OccupationI18n).where(
                    OccupationI18n.occupation_id == occ.id,
                    OccupationI18n.locale == verdict.locale,
                )
            )
        ).scalars().first()
        if i18n is not None:
            i18n.content_source = "council"
            i18n.reviewed_at = dt.datetime.now(dt.UTC)
        occ.published = True
        await session.flush()
        return f"published: {verdict.slug}"

    return f"held ({verdict.verdict}): {verdict.slug}"
