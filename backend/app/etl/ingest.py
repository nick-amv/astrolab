"""Upsert occupation drafts into the DB (unpublished). Idempotent by slug."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.schema import OccupationDraft
from app.models import (
    DataSource,
    Occupation,
    OccupationCountry,
    OccupationI18n,
    OccupationSubject,
)


async def upsert_draft(session: AsyncSession, draft: OccupationDraft) -> Occupation:
    """Create or update one occupation and its i18n / subjects / facts. Never
    flips `published` — publication is the council's job (see review.py)."""
    occ = (
        await session.execute(select(Occupation).where(Occupation.slug == draft.slug))
    ).scalars().first()
    if occ is None:
        occ = Occupation(slug=draft.slug)
        session.add(occ)

    occ.esco_id = draft.esco_id
    occ.onet_code = draft.onet_code
    occ.field_tag = draft.field_tag
    occ.edu_duration_band = draft.edu_duration_band
    occ.regulated = draft.regulated
    occ.riasec = draft.riasec
    occ.riasec_source = draft.riasec_source
    occ.values = draft.values
    await session.flush()  # ensure occ.id

    # i18n (replace per-locale)
    for locale, content in draft.i18n.items():
        i18n_row = (
            await session.execute(
                select(OccupationI18n).where(
                    OccupationI18n.occupation_id == occ.id,
                    OccupationI18n.locale == locale,
                )
            )
        ).scalars().first()
        if i18n_row is None:
            i18n_row = OccupationI18n(occupation_id=occ.id, locale=locale, title=content.title)
            session.add(i18n_row)
        i18n_row.title = content.title
        i18n_row.summary = content.summary
        i18n_row.day_in_life = content.day_in_life
        i18n_row.who_fits = content.who_fits
        i18n_row.content_source = "llm"  # becomes 'council' only on approval

    # subjects (replace all)
    existing_subj = (
        await session.execute(
            select(OccupationSubject).where(OccupationSubject.occupation_id == occ.id)
        )
    ).scalars().all()
    have = {s.subject_code: s for s in existing_subj}
    for code, weight in draft.subjects.items():
        if code in have:
            have[code].weight = weight
        else:
            session.add(
                OccupationSubject(occupation_id=occ.id, subject_code=code, weight=weight)
            )

    # facts (estimate provenance)
    est_source = (
        await session.execute(
            select(DataSource).where(DataSource.name == "llm-estimate")
        )
    ).scalars().first()
    for fact in draft.facts:
        fact_row = (
            await session.execute(
                select(OccupationCountry).where(
                    OccupationCountry.occupation_id == occ.id,
                    OccupationCountry.country == fact.country,
                )
            )
        ).scalars().first()
        if fact_row is None:
            fact_row = OccupationCountry(occupation_id=occ.id, country=fact.country)
            session.add(fact_row)
        fact_row.salary_low = fact.salary_low
        fact_row.salary_high = fact.salary_high
        fact_row.currency = fact.currency
        fact_row.demand_note = fact.demand_note
        fact_row.confidence = fact.confidence
        fact_row.source_id = est_source.id if est_source else None

    await session.flush()
    return occ
