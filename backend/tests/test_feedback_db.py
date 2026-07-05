"""DB-backed test (CI only): match feedback (N2) — upsert, validation, and the
fit-rate that surfaces in the funnel."""

from __future__ import annotations

import uuid

import httpx
from app.db import SessionLocal
from app.etl.ingest import upsert_draft
from app.etl.schema import OccupationDraft
from app.main import app
from app.models import AssessmentSession, Match, MatchFeedback, Occupation, Profile
from app.services.stats import compute_funnel
from sqlalchemy import delete, select

from tests.conftest import requires_db

pytestmark = requires_db


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test")


async def test_feedback_upsert_and_funnel() -> None:
    async with SessionLocal() as s:
        await upsert_draft(
            s,
            OccupationDraft(
                slug="fb-occ",
                field_tag="tech",
                riasec={"I": 0.9},
                i18n={"ru": {"title": "T", "summary": "s", "day_in_life": "d", "who_fits": "w"}},
            ),
        )
        await s.commit()
        occ = (
            await s.execute(select(Occupation).where(Occupation.slug == "fb-occ"))
        ).scalars().first()
        assert occ is not None
        occ_id = occ.id
        p = Profile(anon_token=f"anon-{uuid.uuid4()}", age_band="17-19", locale="ru")
        s.add(p)
        await s.flush()
        ses = AssessmentSession(
            profile_id=p.id, question_bank_version=1, scoring_version=1, status="completed"
        )
        s.add(ses)
        await s.flush()
        s.add(
            Match(
                session_id=ses.id, occupation_id=occ_id, score=0.9, bucket="core",
                rank_det=1, rank_final=1,
            )
        )
        await s.commit()
        sid = str(ses.id)

    async with _client() as c:
        base = f"/api/assessment/{sid}/feedback"

        async def code(slug: str, verdict: str) -> int:
            return (await c.post(base, json={"slug": slug, "verdict": verdict})).status_code

        assert await code("fb-occ", "nope") == 422  # bad verdict
        assert await code("no-such", "fits") == 404  # occupation not in this result
        assert await code("fb-occ", "partial") == 200
        assert await code("fb-occ", "fits") == 200  # re-click overwrites

    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(MatchFeedback).where(MatchFeedback.session_id == uuid.UUID(sid))
            )
        ).scalars().all()
        assert len(rows) == 1 and rows[0].verdict == "fits"  # upsert, not a second row

        funnel = await compute_funnel(s)
        assert funnel["feedback"]["by_verdict"].get("fits", 0) >= 1
        assert funnel["feedback"]["by_bucket"]["core"]["fit_rate"] is not None

        await s.execute(delete(AssessmentSession).where(AssessmentSession.id == uuid.UUID(sid)))
        await s.execute(delete(Occupation).where(Occupation.id == occ_id))
        await s.commit()
