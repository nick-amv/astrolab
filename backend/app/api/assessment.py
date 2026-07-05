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
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment import AnswerItem, compute_scores
from app.assessment.cv import extract_cv
from app.assessment.interview import generate_statements, select_statements
from app.assessment.pipeline import enrich_with_llm, store_deterministic
from app.assessment.read import result_payload
from app.config import settings
from app.db import get_session
from app.models import (
    AiInterview,
    Answer,
    AssessmentSession,
    Match,
    MatchFeedback,
    Occupation,
    QuestionBank,
    QuestionI18n,
    Report,
    ScoringConfig,
    TraitScore,
)
from app.models import (
    Profile as ProfileRow,
)
from app.security.tokens import hash_token, new_token

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
    profile_row = (
        await session.execute(select(ProfileRow).where(ProfileRow.id == ses.profile_id))
    ).scalars().first()
    # Adults (working, or 24+) get the CV branch instead of the subjects grid.
    adult = bool(
        profile_row
        and (profile_row.education_stage == "working" or profile_row.age_band == "24+")
    )
    return {"blocks": blocks, "adult": adult}


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
    # Deterministic match only — fast, never blocks on the LLM. The result page
    # fires /enrich afterwards for the LLM re-rank + "why you" (DESIGN §4.4).
    await store_deterministic(session, ses)
    return {"scores": scores, "scoring_version": ses.scoring_version}


@router.post("/{session_id}/enrich")
async def enrich(
    session_id: str, locale: str = "ru", session: AsyncSession = Depends(get_session)
) -> dict:
    """Run the LLM re-rank/explain (degradable) and return the (possibly enriched)
    result. Called by the result page after it shows the deterministic result, so
    the user never waits on the shared LLM."""
    ses = await _get_session_or_404(session, session_id)
    await enrich_with_llm(session, ses)
    payload = await result_payload(session, ses, locale)
    if payload is None:
        raise HTTPException(status_code=409, detail="not scored yet")
    return payload


# --------------------------------------------------------------------------- #
# result
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# adult CV (Wave 5)
# --------------------------------------------------------------------------- #
class CvIn(BaseModel):
    text: str


@router.post("/{session_id}/cv")
async def submit_cv(
    session_id: str, body: CvIn, session: AsyncSession = Depends(get_session)
) -> dict:
    ses = await _get_session_or_404(session, session_id)
    profile_row = (
        await session.execute(select(ProfileRow).where(ProfileRow.id == ses.profile_id))
    ).scalars().first()
    locale = profile_row.locale if profile_row else "ru"
    cv = await extract_cv(body.text, locale)
    if cv and profile_row:
        profile_row.cv = cv
        # re-enrich with the CV context on the next result load
        await session.execute(
            update(Match)
            .where(Match.session_id == ses.id)
            .values(llm_reason=None, rank_llm=None, rank_final=Match.rank_det)
        )
        await session.commit()
    return {"ok": cv is not None}


# --------------------------------------------------------------------------- #
# optional mini-interview
# --------------------------------------------------------------------------- #
@router.get("/{session_id}/interview")
async def interview_questions(
    session_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    ses = await _get_session_or_404(session, session_id)
    traits = (
        await session.execute(select(TraitScore).where(TraitScore.session_id == ses.id))
    ).scalars().all()
    by_kind = {t.kind: t.vector for t in traits}
    riasec = by_kind.get("riasec")
    if not riasec:
        raise HTTPException(status_code=409, detail="not scored yet")
    profile_row = (
        await session.execute(select(ProfileRow).where(ProfileRow.id == ses.profile_id))
    ).scalars().first()
    locale = profile_row.locale if profile_row else "ru"
    # LLM-personalised questions from THIS profile; degrade to the static set.
    profile = {
        "riasec": riasec,
        "values": by_kind.get("values", {}),
        "subjects": by_kind.get("subjects", {}),
    }
    stmts = await generate_statements(profile, locale)
    personalized = stmts is not None
    if stmts is None:
        stmts = select_statements(riasec, locale=locale)
    return {"statements": stmts, "personalized": personalized}


class InterviewItemIn(BaseModel):
    text: str
    value: float


class InterviewIn(BaseModel):
    items: list[InterviewItemIn] = Field(default_factory=list)


@router.post("/{session_id}/interview")
async def submit_interview(
    session_id: str, body: InterviewIn, session: AsyncSession = Depends(get_session)
) -> dict:
    ses = await _get_session_or_404(session, session_id)
    # The statement text is echoed back by the client (works for both the static
    # and the LLM-generated set, whose ids aren't in any static table).
    transcript = [
        {"text": it.text[:400], "value": max(0.0, min(1.0, it.value))}
        for it in body.items
        if it.text.strip()
    ]
    await session.execute(delete(AiInterview).where(AiInterview.session_id == ses.id))
    session.add(AiInterview(session_id=ses.id, transcript={"items": transcript}))
    # Mark the LLM enrichment stale so the result re-runs it WITH the interview.
    await session.execute(
        update(Match)
        .where(Match.session_id == ses.id)
        .values(llm_reason=None, rank_llm=None, rank_final=Match.rank_det)
    )
    await session.commit()
    return {"saved": len(transcript)}


@router.get("/{session_id}/result")
async def result(
    session_id: str, locale: str = "ru", session: AsyncSession = Depends(get_session)
) -> dict:
    ses = await _get_session_or_404(session, session_id)
    payload = await result_payload(session, ses, locale)
    if payload is None:
        raise HTTPException(status_code=409, detail="not scored yet")
    return payload


class FeedbackIn(BaseModel):
    slug: str
    verdict: str  # fits | partial | not_me


@router.post("/{session_id}/feedback")
async def submit_feedback(
    session_id: str, body: FeedbackIn, session: AsyncSession = Depends(get_session)
) -> dict:
    """Record the user's 'that's me / partly / not me' reaction to one of THIS
    session's matched occupations. Upsert (a re-click overwrites). Our only
    signal on match quality (N2)."""
    ses = await _get_session_or_404(session, session_id)
    if body.verdict not in ("fits", "partial", "not_me"):
        raise HTTPException(status_code=422, detail="bad verdict")
    # only an occupation this session was actually matched to can be rated
    occ_id = (
        await session.execute(
            select(Match.occupation_id)
            .join(Occupation, Occupation.id == Match.occupation_id)
            .where(Match.session_id == ses.id, Occupation.slug == body.slug)
        )
    ).scalars().first()
    if occ_id is None:
        raise HTTPException(status_code=404, detail="occupation not in this result")
    row = (
        await session.execute(
            select(MatchFeedback).where(
                MatchFeedback.session_id == ses.id,
                MatchFeedback.occupation_id == occ_id,
            )
        )
    ).scalars().first()
    if row is None:
        row = MatchFeedback(session_id=ses.id, occupation_id=occ_id)
        session.add(row)
    row.verdict = body.verdict
    await session.commit()
    return {"ok": True, "verdict": body.verdict}


class ShareOut(BaseModel):
    token: str


@router.post("/{session_id}/share", response_model=ShareOut)
async def create_share(
    session_id: str, session: AsyncSession = Depends(get_session)
) -> ShareOut:
    """Create (or reuse) a persistent, hashed share link for a scored session.
    The raw token is returned once and only its SHA-256 hash is stored."""
    ses = await _get_session_or_404(session, session_id)
    payload = await result_payload(session, ses, "ru")
    if payload is None:
        raise HTTPException(status_code=409, detail="not scored yet")
    token = new_token()
    session.add(
        Report(
            session_id=ses.id,
            kind="teen",
            token_hash=hash_token(token),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=settings.report_ttl_days),
        )
    )
    await session.commit()
    return ShareOut(token=token)


# N5: a parent report is only meaningful for a teen. The gate is server-side —
# adults get no button AND the API refuses (422) even if called directly.
_TEEN_BANDS = ("14-16", "17-19")


@router.post("/{session_id}/parent-share", response_model=ShareOut)
async def create_parent_share(
    session_id: str, session: AsyncSession = Depends(get_session)
) -> ShareOut:
    """Create a hashed link to a warm, no-raw-answers parent view. Teen sessions
    only; an adult session (or one with no age) is refused with 422."""
    ses = await _get_session_or_404(session, session_id)
    prof = (
        await session.execute(select(ProfileRow).where(ProfileRow.id == ses.profile_id))
    ).scalars().first()
    if prof is None or prof.age_band not in _TEEN_BANDS:
        raise HTTPException(status_code=422, detail="parent report is for teens only")
    payload = await result_payload(session, ses, "ru")
    if payload is None:
        raise HTTPException(status_code=409, detail="not scored yet")
    token = new_token()
    session.add(
        Report(
            session_id=ses.id,
            kind="parent",
            token_hash=hash_token(token),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=settings.report_ttl_days),
        )
    )
    await session.commit()
    return ShareOut(token=token)
