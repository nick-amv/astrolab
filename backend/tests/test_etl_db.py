"""DB-backed ETL test (CI only): ingest a draft, apply an approved council
verdict, and confirm it publishes; a split verdict must NOT publish."""

from __future__ import annotations

from app.config import settings
from app.etl.ingest import upsert_draft
from app.etl.review import apply_verdict
from app.etl.schema import ModelVote, OccupationDraft, ReviewVerdict
from app.models import ContentReview, Occupation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.conftest import requires_db

pytestmark = requires_db


def _session():
    engine = create_async_engine(settings.database_url)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession), engine


def _draft(slug: str) -> OccupationDraft:
    return OccupationDraft(
        slug=slug,
        field_tag="tech",
        riasec={"I": 0.9, "C": 0.6},
        i18n={"ru": {"title": "Test", "summary": "s", "day_in_life": "d", "who_fits": "w"}},
    )


async def test_ingest_then_approved_publishes() -> None:
    Session, engine = _session()
    async with Session() as s:
        await upsert_draft(s, _draft("etl-approve"))
        await s.commit()
        occ = (
            await s.execute(select(Occupation).where(Occupation.slug == "etl-approve"))
        ).scalars().first()
        assert occ is not None and occ.published is False  # not published on ingest

        verdict = ReviewVerdict(
            slug="etl-approve",
            verdict="approved",
            models=[ModelVote(model="gpt", verdict="approve")],
        )
        status = await apply_verdict(s, verdict)
        await s.commit()
        assert "published" in status

        occ = (
            await s.execute(select(Occupation).where(Occupation.slug == "etl-approve"))
        ).scalars().first()
        assert occ.published is True
        review = (
            await s.execute(
                select(ContentReview).where(ContentReview.occupation_id == occ.id)
            )
        ).scalars().first()
        assert review is not None and review.verdict == "approved"
    await engine.dispose()


async def test_split_verdict_does_not_publish() -> None:
    Session, engine = _session()
    async with Session() as s:
        await upsert_draft(s, _draft("etl-split"))
        await s.commit()
        verdict = ReviewVerdict(
            slug="etl-split",
            verdict="split",
            models=[
                ModelVote(model="a", verdict="approve"),
                ModelVote(model="b", verdict="reject"),
            ],
            factual_flags=["disputed"],
        )
        status = await apply_verdict(s, verdict)
        await s.commit()
        assert "held" in status
        occ = (
            await s.execute(select(Occupation).where(Occupation.slug == "etl-split"))
        ).scalars().first()
        assert occ.published is False  # split → stays unpublished
    await engine.dispose()
