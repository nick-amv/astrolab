"""Assessment API: start a session, serve questions, take answers, score, and
return a result (profile + matched occupations).

Anonymous-first: a session is created with a random anon_token and identified by
its UUID (an unguessable capability). No PII is required to take the test or see
the result (PRIVACY_MODEL.md).
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment import AnswerItem, compute_scores
from app.db import get_session
from app.matching import Profile, match
from app.models import (
    Answer,
    AssessmentSession,
    Occupation,
    OccupationI18n,
    QuestionBank,
    QuestionI18n,
    ScoringConfig,
    TraitScore,
)
from app.models import (
    Profile as ProfileRow,
)
from app.security.tokens import new_token
from app.services.catalog import load_published_vectors

router = APIRouter(prefix="/api/assessment", tags=["assessment"])


# --------------------------------------------------------------------------- #
# start
# --------------------------------------------------------------------------- #
class StartIn(BaseModel):
    age_band: str
    locale: str = "ru"
    education_stage: str | None = None
    country_live: str | None = "RU"
    country_study: str | None = "RU"


class StartOut(BaseModel):
    session_id: str
    anon_token: str
    question_bank_version: int


async def _latest_version(session: AsyncSession) -> int:
    v = (
        await session.execute(
            select(QuestionBank.version).order_by(QuestionBank.version.desc()).limit(1)
        )
    ).scalar()
    return int(v or 1)


async def _scoring_version(session: AsyncSession) -> int:
    v = (
        await session.execute(
            select(ScoringConfig.version).order_by(ScoringConfig.version.desc()).limit(1)
        )
    ).scalar()
    return int(v or 1)


@router.post("/start", response_model=StartOut)
async def start(body: StartIn, session: AsyncSession = Depends(get_session)) -> StartOut:
    token = new_token()
    profile = ProfileRow(
        anon_token=token,
        age_band=body.age_band,
        locale=body.locale,
        country_live=body.country_live,
        country_study=body.country_study,
        education_stage=body.education_stage,
    )
    session.add(profile)
    await session.flush()

    qbv = await _latest_version(session)
    scv = await _scoring_version(session)
    ses = AssessmentSession(
        profile_id=profile.id,
        question_bank_version=qbv,
        scoring_version=scv,
        status="started",
    )
    session.add(ses)
    await session.commit()
    return StartOut(session_id=str(ses.id), anon_token=token, question_bank_version=qbv)


# --------------------------------------------------------------------------- #
# questions
# --------------------------------------------------------------------------- #
async def _get_session_or_404(session: AsyncSession, session_id: str) -> AssessmentSession:
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    ses = (
        await session.execute(select(AssessmentSession).where(AssessmentSession.id == sid))
    ).scalars().first()
    if ses is None:
        raise HTTPException(status_code=404, detail="session not found")
    return ses


@router.get("/{session_id}/questions")
async def questions(
    session_id: str, locale: str = "ru", session: AsyncSession = Depends(get_session)
) -> dict:
    ses = await _get_session_or_404(session, session_id)
    qs = (
        await session.execute(
            select(QuestionBank).where(
                QuestionBank.version == ses.question_bank_version,
                QuestionBank.active.is_(True),
            )
        )
    ).scalars().all()
    i18n = (
        await session.execute(
            select(QuestionI18n).where(
                QuestionI18n.question_id.in_([q.id for q in qs])
            )
        )
    ).scalars().all()
    text_by = {(str(r.question_id), r.locale): r.text for r in i18n}

    def txt(qid: uuid.UUID) -> str:
        return (
            text_by.get((str(qid), locale))
            or text_by.get((str(qid), "ru"))
            or ""
        )

    blocks: dict[str, list[dict]] = {"A": [], "B": [], "C": []}
    for q in sorted(qs, key=lambda q: (q.block, q.dimension)):
        if q.block in blocks:
            blocks[q.block].append(
                {"id": str(q.id), "dimension": q.dimension, "text": txt(q.id)}
            )
    return {"blocks": blocks}


# --------------------------------------------------------------------------- #
# answers
# --------------------------------------------------------------------------- #
class AnswerIn(BaseModel):
    question_id: str
    value: float


class AnswersIn(BaseModel):
    answers: list[AnswerIn] = Field(default_factory=list)


@router.post("/{session_id}/answers")
async def submit_answers(
    session_id: str, body: AnswersIn, session: AsyncSession = Depends(get_session)
) -> dict:
    ses = await _get_session_or_404(session, session_id)
    if not body.answers:
        return {"saved": 0}
    qids = [uuid.UUID(a.question_id) for a in body.answers]
    # replace existing answers for these questions (idempotent)
    await session.execute(
        delete(Answer).where(Answer.session_id == ses.id, Answer.question_id.in_(qids))
    )
    for a in body.answers:
        session.add(
            Answer(
                session_id=ses.id,
                question_id=uuid.UUID(a.question_id),
                value=max(0.0, min(1.0, a.value)),
            )
        )
    if ses.status == "started":
        ses.status = "in_progress"
    await session.commit()
    return {"saved": len(body.answers)}


# --------------------------------------------------------------------------- #
# score
# --------------------------------------------------------------------------- #
async def _compute_and_store(session: AsyncSession, ses: AssessmentSession) -> dict[str, dict]:
    rows = (
        await session.execute(
            select(
                Answer.value,
                QuestionBank.block,
                QuestionBank.dimension,
                QuestionBank.klimov_tag,
            )
            .join(QuestionBank, QuestionBank.id == Answer.question_id)
            .where(Answer.session_id == ses.id)
        )
    ).all()
    items = [
        AnswerItem(block=b, dimension=d, value=float(v), klimov=k) for (v, b, d, k) in rows
    ]
    scores = compute_scores(items)

    # upsert trait_scores per kind
    await session.execute(delete(TraitScore).where(TraitScore.session_id == ses.id))
    for kind, vector in scores.items():
        session.add(TraitScore(session_id=ses.id, kind=kind, vector=vector))
    ses.status = "completed"
    ses.finished_at = dt.datetime.now(dt.UTC)
    await session.commit()
    return scores


@router.post("/{session_id}/score")
async def score(session_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    ses = await _get_session_or_404(session, session_id)
    scores = await _compute_and_store(session, ses)
    return {"scores": scores, "scoring_version": ses.scoring_version}


# --------------------------------------------------------------------------- #
# result
# --------------------------------------------------------------------------- #
@router.get("/{session_id}/result")
async def result(
    session_id: str, locale: str = "ru", session: AsyncSession = Depends(get_session)
) -> dict:
    ses = await _get_session_or_404(session, session_id)
    profile_row = (
        await session.execute(select(ProfileRow).where(ProfileRow.id == ses.profile_id))
    ).scalars().first()

    traits = (
        await session.execute(select(TraitScore).where(TraitScore.session_id == ses.id))
    ).scalars().all()
    by_kind = {t.kind: t.vector for t in traits}
    if not by_kind:
        raise HTTPException(status_code=409, detail="not scored yet")

    cfg = (
        await session.execute(select(ScoringConfig).order_by(ScoringConfig.version.desc()))
    ).scalars().first()

    profile = Profile(
        riasec=by_kind.get("riasec", {}),
        values=by_kind.get("values", {}),
        subjects=by_kind.get("subjects", {}),
        age_band=profile_row.age_band if profile_row else "17-19",
    )
    vectors = await load_published_vectors(session)
    scored = match(profile, vectors, cfg.weights if cfg else {})

    # localize occupation titles for display
    slugs = [s.occupation.slug for s in scored if s.bucket != "none"]
    titles: dict[str, str] = {}
    if slugs:
        occ_rows = (
            await session.execute(select(Occupation).where(Occupation.slug.in_(slugs)))
        ).scalars().all()
        occ_ids = {str(o.id): o.slug for o in occ_rows}
        i18n = (
            await session.execute(
                select(OccupationI18n).where(
                    OccupationI18n.occupation_id.in_([o.id for o in occ_rows])
                )
            )
        ).scalars().all()
        t = {(str(r.occupation_id), r.locale): r.title for r in i18n}
        for oid, slug in occ_ids.items():
            titles[slug] = t.get((oid, locale)) or t.get((oid, "ru")) or slug

    def bucket(name: str) -> list[dict]:
        return [
            {
                "slug": s.occupation.slug,
                "title": titles.get(s.occupation.slug, s.occupation.slug),
                "score": round(s.score, 3),
            }
            for s in scored
            if s.bucket == name
        ]

    return {
        "profile": {
            "riasec": by_kind.get("riasec", {}),
            "klimov": by_kind.get("klimov", {}),
            "values": by_kind.get("values", {}),
            "subjects": by_kind.get("subjects", {}),
        },
        "age_band": profile_row.age_band if profile_row else None,
        "buckets": {
            "core": bucket("core"),
            "near": bucket("near"),
            "dark_horse": bucket("dark_horse"),
        },
    }
