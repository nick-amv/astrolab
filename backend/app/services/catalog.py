"""Read-side catalog queries: load occupations for matching and for the public
catalog. Only `published = true` rows are ever exposed."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching import OccupationVec
from app.models import (
    DataSource,
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


async def get_occupation_detail(
    session: AsyncSession, slug: str, locale: str, country: str | None = None
) -> dict | None:
    """Full public detail for one published occupation, localized with fallback.

    When ``country`` is given, only that country's facts are returned — so an EN
    (US) page never carries RU/RUB facts, not even in the client fetch cache."""
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
    if country:
        countries = [c for c in countries if c.country == country]

    # provenance key per fact (bls-oews / rosstat-ozpp / llm-estimate) so the UI
    # can badge real data vs an estimate instead of a flat "estimate" on both.
    src_ids = {c.source_id for c in countries if c.source_id}
    src_by_id: dict = {}
    if src_ids:
        srcs = (
            await session.execute(select(DataSource).where(DataSource.id.in_(src_ids)))
        ).scalars().all()
        src_by_id = {s.id: s.name for s in srcs}

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
                # US OEWS wages are annual; RU figures are monthly. Surfacing the
                # period stops a US visitor reading an annual number as monthly.
                "period": "year" if c.currency == "USD" else "month",
                "demand_note": c.demand_note,
                "confidence": c.confidence,  # 'estimate' → UI marks as estimate
                "source": src_by_id.get(c.source_id),  # bls-oews | rosstat-ozpp | llm-estimate
                "as_of_date": c.as_of_date.isoformat() if c.as_of_date else None,
            }
            for c in countries
        ],
    }


async def list_published(
    session: AsyncSession, locale: str, country: str | None = None
) -> list[dict]:
    occs = (
        await session.execute(
            select(Occupation).where(Occupation.published.is_(True)).order_by(Occupation.slug)
        )
    ).scalars().all()
    if not occs:
        return []
    occ_ids = [o.id for o in occs]
    i18n_rows = (
        await session.execute(
            select(OccupationI18n).where(OccupationI18n.occupation_id.in_(occ_ids))
        )
    ).scalars().all()
    title_by = {(str(r.occupation_id), r.locale): r.title for r in i18n_rows}

    # salary for the user's country (for the catalog salary filter). None when
    # a country has no fact (e.g. US actors) — the filter just skips it.
    fact_by: dict[str, dict] = {}
    if country:
        facts = (
            await session.execute(
                select(OccupationCountry).where(
                    OccupationCountry.occupation_id.in_(occ_ids),
                    OccupationCountry.country == country,
                )
            )
        ).scalars().all()
        fact_by = {
            str(c.occupation_id): {
                "salary_low": c.salary_low,
                "salary_high": c.salary_high,
                "currency": c.currency,
                "period": "year" if c.currency == "USD" else "month",
            }
            for c in facts
        }

    out = []
    for o in occs:
        title = (
            title_by.get((str(o.id), locale))
            or title_by.get((str(o.id), "en"))
            or title_by.get((str(o.id), "ru"))
            or o.slug
        )
        item = {
            "slug": o.slug,
            "title": title,
            "field_tag": o.field_tag,
            "edu_duration_band": o.edu_duration_band,
        }
        item.update(fact_by.get(str(o.id), {}))
        out.append(item)
    return out
