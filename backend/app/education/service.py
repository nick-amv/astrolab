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
# Scorecard link-out (EN-2). FR = ONISEP + Parcoursup (FR-2). DE = BERUFENET +
# Hochschulstart (DE-2).
_SUPPORTED = {"RU", "US", "ES", "FR", "DE"}

# First month of the admission cycle per country. The US senior year runs
# Aug -> May, so a plain MM-DD sort would show January deadlines before the
# August "build your college list" step. RU's cycle sits inside one calendar
# year (Feb -> Aug), so it defaults to January. Spain's curso starts in Sep.
# France's Parcoursup cycle wraps the year (explore in Nov -> rentrée in Sep),
# so it starts in November like the US senior-year build-list step. Germany's
# cycle wraps too (explore in Oct -> Ausbildung/Wintersemester start next Sep-Oct),
# so it starts in October.
_CYCLE_START = {"US": 8, "ES": 9, "FR": 11, "DE": 10}


def _cycle_key(date_rule: str, start_month: int) -> tuple[int, int]:
    """Sort key that orders MM-DD milestones within a country's own cycle."""
    try:
        mm, dd = (int(x) for x in date_rule.split("-")[:2])
    except ValueError:
        return (99, 0)  # relative:/unknown rules sort last
    return ((mm - start_month) % 12, dd)


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
        # An occupation maps to domains in several countries; keep only this
        # country's (otherwise RU OKSO majors leak onto a US page and vice versa).
        doms = (
            await session.execute(
                select(EduDomain).where(
                    EduDomain.id.in_(domain_ids), EduDomain.country == country
                )
            )
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
    start_month = _CYCLE_START.get(country, 1)
    milestones = [
        {"date_rule": m.date_rule, "title": m.title_key}
        for m in sorted(ms_rows, key=lambda m: _cycle_key(m.date_rule, start_month))
    ]

    return {
        "country": country,
        "available": True,
        "note": note,
        "domains": domains,
        "milestones": milestones,
    }
