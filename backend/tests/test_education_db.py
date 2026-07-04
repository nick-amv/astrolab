"""DB-backed test (CI only): education paths are scoped to the requested country
so RU (OKSO) and US (CIP) majors never leak onto each other's pages. Guards the
EN-2 regression where an occupation mapped to domains in both countries returned
all of them regardless of ?country=."""

from __future__ import annotations

from app.config import settings
from app.education.service import get_education
from app.etl.ingest import upsert_draft
from app.etl.schema import OccupationDraft
from app.models import EduDomain, EduRequirement, Occupation, OccupationEdu
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.conftest import requires_db

pytestmark = requires_db


def _session():
    engine = create_async_engine(settings.database_url)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession), engine


async def test_education_is_country_scoped() -> None:
    Session, engine = _session()
    async with Session() as s:
        await upsert_draft(
            s,
            OccupationDraft(
                slug="edu-country-test",
                field_tag="tech",
                riasec={"I": 0.9},
                i18n={"ru": {"title": "T", "summary": "s", "day_in_life": "d", "who_fits": "w"}},
            ),
        )
        await s.commit()
        occ = (
            await s.execute(select(Occupation).where(Occupation.slug == "edu-country-test"))
        ).scalars().first()
        assert occ is not None

        ru = EduDomain(country="RU", code="09.03.01", title_key="RU major")
        us = EduDomain(country="US", code="11.0701", title_key="US major")
        s.add_all([ru, us])
        await s.flush()
        s.add_all(
            [
                EduRequirement(domain_id=ru.id, data={"level": "bak", "ege": []}),
                EduRequirement(domain_id=us.id, data={"level": "Bachelor's", "ege": []}),
                OccupationEdu(occupation_id=occ.id, domain_id=ru.id, weight=1.0),
                OccupationEdu(occupation_id=occ.id, domain_id=us.id, weight=1.0),
            ]
        )
        await s.commit()

        us_edu = await get_education(s, "edu-country-test", "US")
        assert {d["code"] for d in us_edu["domains"]} == {"11.0701"}  # RU must NOT leak

        ru_edu = await get_education(s, "edu-country-test", "RU")
        assert {d["code"] for d in ru_edu["domains"]} == {"09.03.01"}  # US must NOT leak
    await engine.dispose()
