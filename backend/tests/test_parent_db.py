"""DB-backed test (CI only): N5 parent report — the teen-only server gate
(adult session -> 422), the no-raw-answers payload, and that a normal share
token does not resolve on the parent endpoint."""

from __future__ import annotations

import json
import uuid

import pytest
from app.api.assessment import create_parent_share
from app.api.parent import read_parent
from app.db import SessionLocal
from app.etl.ingest import upsert_draft
from app.etl.schema import OccupationDraft
from app.models import AssessmentSession, Match, Occupation, Profile, TraitScore
from fastapi import HTTPException
from sqlalchemy import delete, select

from tests.conftest import requires_db

pytestmark = requires_db


async def _make_session(age_band: str) -> tuple[str, uuid.UUID]:
    async with SessionLocal() as s:
        await upsert_draft(
            s,
            OccupationDraft(
                slug="parent-occ",
                field_tag="science",
                riasec={"I": 0.9, "A": 0.6},
                i18n={"ru": {"title": "T", "summary": "s", "day_in_life": "d", "who_fits": "w"}},
            ),
        )
        await s.commit()
        occ = (
            await s.execute(select(Occupation).where(Occupation.slug == "parent-occ"))
        ).scalars().first()
        assert occ is not None
        p = Profile(anon_token=f"anon-{uuid.uuid4()}", age_band=age_band, locale="ru")
        s.add(p)
        await s.flush()
        ses = AssessmentSession(
            profile_id=p.id, question_bank_version=1, scoring_version=1, status="completed"
        )
        s.add(ses)
        await s.flush()
        s.add(TraitScore(session_id=ses.id, kind="riasec", vector={"I": 0.9, "A": 0.6, "R": 0.2}))
        s.add(
            Match(
                session_id=ses.id, occupation_id=occ.id, score=0.9, bucket="core",
                rank_det=1, rank_final=1,
                # simulates a rerank reason shaped by the teen's private interview/CV
                llm_reason="SENSITIVE_INTERVIEW_DERIVED text about the teen",
            )
        )
        await s.commit()
        return str(ses.id), occ.id


async def test_parent_gate_and_payload() -> None:
    teen_sid, occ_id = await _make_session("17-19")
    adult_sid, _ = await _make_session("24+")

    async with SessionLocal() as s:
        # adult session -> refused (422), even calling the API directly
        with pytest.raises(HTTPException) as ei:
            await create_parent_share(adult_sid, s)
        assert ei.value.status_code == 422

        # teen session -> token
        out = await create_parent_share(teen_sid, s)
        token = out.token
        assert token

    async with SessionLocal() as s:
        view = await read_parent(token, "ru", s)
        assert len(view["axes"]) == 2 and view["axes"][0]["axis"] == "I"
        assert len(view["strengths"]) >= 3
        assert len(view["support"]) == 3
        assert view["professions"] and view["professions"][0]["title"] == "T"
        # 'why' is curated who_fits ('w'), NEVER the interview/CV-derived llm_reason
        assert view["professions"][0]["why"] == "w"
        # no raw answers / full list / LLM-derived personal content ever leak
        assert "answers" not in view and "buckets" not in view
        assert "SENSITIVE_INTERVIEW_DERIVED" not in json.dumps(view, ensure_ascii=False)

        # a bogus token 404s
        with pytest.raises(HTTPException) as ei:
            await read_parent("nope", "ru", s)
        assert ei.value.status_code == 404

    async with SessionLocal() as s:
        for sid in (teen_sid, adult_sid):
            await s.execute(delete(AssessmentSession).where(AssessmentSession.id == uuid.UUID(sid)))
        await s.execute(delete(Occupation).where(Occupation.id == occ_id))
        await s.commit()
