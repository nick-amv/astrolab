"""Education paths for an occupation, by country of study."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    EduDomain,
    EduRequirement,
    Milestone,
    Occupation,
    OccupationEdu,
)

# Honest fallback for countries we haven't curated: point at official sources,
# do NOT LLM-generate admission paths (design rule P5). US = CIP majors + College
# Scorecard link-out (EN-2).
_SUPPORTED = {"RU", "US"}


async def get_education(session: AsyncSession, slug: str, country: str) -> dict:
    country = (country or "RU").upper()
    if country not in _SUPPORTED:
        return {
            "country": country,
            "available": False,
            "domains": [],
            "milestones": [],
        }

    occ = (
        await session.execute(select(Occupation).where(Occupation.slug == slug))
    ).scalars().first()
    if occ is None:
        return {"country": country, "available": True, "domains": [], "milestones": []}

    domain_ids = (
        await session.execute(
            select(OccupationEdu.domain_id).where(OccupationEdu.occupation_id == occ.id)
        )
    ).scalars().all()

    domains: list[dict] = []
    note = None
    if domain_ids:
        doms = (
            await session.execute(select(EduDomain).where(EduDomain.id.in_(domain_ids)))
        ).scalars().all()
        reqs = (
            await session.execute(
                select(EduRequirement).where(EduRequirement.domain_id.in_(domain_ids))
            )
        ).scalars().all()
        req_by_domain = {str(r.domain_id): r.data for r in reqs}
        for d in sorted(doms, key=lambda d: d.code):
            data = req_by_domain.get(str(d.id), {})
            note = note or data.get("note")
            domains.append(
                {
                    "code": d.code,
                    "title": d.title_key,
                    "level": data.get("level"),
                    "ege": data.get("ege", []),
                    "as_of": data.get("as_of"),
                }
            )

    ms_rows = (
        await session.execute(
            select(Milestone).where(
                Milestone.country == country, Milestone.education_stage == "school"
            )
        )
    ).scalars().all()
    milestones = [
        {"date_rule": m.date_rule, "title": m.title_key}
        for m in sorted(ms_rows, key=lambda m: m.date_rule)
    ]

    return {
        "country": country,
        "available": True,
        "note": note,
        "domains": domains,
        "milestones": milestones,
    }
