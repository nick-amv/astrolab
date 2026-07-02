"""Read-side catalog queries: load occupations for matching and for the public
catalog. Only `published = true` rows are ever exposed."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching import OccupationVec
from app.models import (
    Occupation,
    OccupationCountry,
    OccupationI18n,
    OccupationSubject,
)


async def load_published_vectors(session: AsyncSession) -> list[OccupationVec]:
    """All published occupations as scoring vectors (riasec/values/subjects)."""
    occs = (
        await session.execute(select(Occupation).where(Occupation.published.is_(True)))
    ).scalars().all()
    if not occs:
        return []
    subj_rows = (await session.execute(select(OccupationSubject))).scalars().all()
    subjects_by_occ: dict[str, dict[str, float]] = {}
    for row in subj_rows:
        subjects_by_occ.setdefault(str(row.occupation_id), {})[row.subject_code] = row.weight

    vectors: list[OccupationVec] = []
    for o in occs:
        vectors.append(
            OccupationVec(
                id=str(o.id),
                slug=o.slug,
                riasec=o.riasec or {},
                values=o.values or {},
                subjects=subjects_by_occ.get(str(o.id), {}),
                edu_years=_band_to_years(o.edu_duration_band),
                field_tag=o.field_tag,
            )
        )
    return vectors


def _band_to_years(band: str | None) -> float | None:
    return {
        "short": 1.0,
        "vocational": 2.5,
        "bachelor": 4.0,
        "specialist": 5.0,
        "master": 6.0,
        "long": 8.0,
    }.get(band or "")


async def get_occupation_detail(session: AsyncSession, slug: str, locale: str) -> dict | None:
    """Full public detail for one published occupation, localized with fallback."""
    occ = (
        await session.execute(
            select(Occupation).where(
                Occupation.slug == slug, Occupation.published.is_(True)
            )
        )
    ).scalars().first()
    if occ is None:
        return None

    i18n_rows = (
        await session.execute(
            select(OccupationI18n).where(OccupationI18n.occupation_id == occ.id)
        )
    ).scalars().all()
    by_locale = {r.locale: r for r in i18n_rows}
    chosen = by_locale.get(locale) or by_locale.get("en") or by_locale.get("ru")

    countries = (
        await session.execute(
            select(OccupationCountry).where(OccupationCountry.occupation_id == occ.id)
        )
    ).scalars().all()

    return {
        "slug": occ.slug,
        "riasec": occ.riasec or {},
        "riasec_source": occ.riasec_source,
        "regulated": occ.regulated,
        "title": chosen.title if chosen else occ.slug,
        "summary": chosen.summary if chosen else None,
        "day_in_life": chosen.day_in_life if chosen else None,
        "who_fits": chosen.who_fits if chosen else None,
        "content_source": chosen.content_source if chosen else None,
        "facts": [
            {
                "country": c.country,
                "salary_low": c.salary_low,
                "salary_high": c.salary_high,
                "currency": c.currency,
                "demand_note": c.demand_note,
                "confidence": c.confidence,  # 'estimate' → UI marks as estimate
                "as_of_date": c.as_of_date.isoformat() if c.as_of_date else None,
            }
            for c in countries
        ],
    }


async def list_published(session: AsyncSession, locale: str) -> list[dict]:
    occs = (
        await session.execute(
            select(Occupation).where(Occupation.published.is_(True)).order_by(Occupation.slug)
        )
    ).scalars().all()
    if not occs:
        return []
    i18n_rows = (
        await session.execute(
            select(OccupationI18n).where(
                OccupationI18n.occupation_id.in_([o.id for o in occs])
            )
        )
    ).scalars().all()
    title_by = {(str(r.occupation_id), r.locale): r.title for r in i18n_rows}
    out = []
    for o in occs:
        title = (
            title_by.get((str(o.id), locale))
            or title_by.get((str(o.id), "en"))
            or title_by.get((str(o.id), "ru"))
            or o.slug
        )
        out.append({"slug": o.slug, "title": title})
    return out
