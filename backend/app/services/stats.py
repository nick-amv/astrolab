"""Assessment funnel stats, derived from the DB (no extra tracking needed).

Every session and answer is already recorded, so "started → how far → finished
/ dropped" is a pure query over `assessment_sessions` + `answers`. Used by the
admin stats endpoint and the scripts/stats.py CLI.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AiInterview,
    Answer,
    AssessmentSession,
    Match,
    MatchFeedback,
    Profile,
    QuestionBank,
    Report,
)


def _fit_rate(d: dict[str, int]) -> float | None:
    """Match-quality score for a bucket: 'partly' counts half. None if no votes."""
    total = d["fits"] + d["partial"] + d["not_me"]
    return round((d["fits"] + 0.5 * d["partial"]) / total, 3) if total else None


async def _scalar(session: AsyncSession, stmt) -> int:
    return int((await session.execute(stmt)).scalar() or 0)


async def compute_funnel(session: AsyncSession) -> dict:
    now = dt.datetime.now(dt.UTC)
    S = AssessmentSession

    total = await _scalar(session, select(func.count()).select_from(S))
    completed = await _scalar(
        session, select(func.count()).select_from(S).where(S.status == "completed")
    )

    # sessions by status
    status_rows = (
        await session.execute(select(S.status, func.count()).group_by(S.status))
    ).all()
    by_status = {str(s): int(c) for s, c in status_rows}

    # distinct sessions that answered each block (A interests, B subjects, C values)
    block_rows = (
        await session.execute(
            select(QuestionBank.block, func.count(func.distinct(Answer.session_id)))
            .join(QuestionBank, QuestionBank.id == Answer.question_id)
            .group_by(QuestionBank.block)
        )
    ).all()
    by_block = {str(b): int(c) for b, c in block_rows}

    enriched = await _scalar(
        session,
        select(func.count(func.distinct(Match.session_id))).where(Match.llm_reason.isnot(None)),
    )
    shared = await _scalar(
        session, select(func.count(func.distinct(Report.session_id)))
    )
    interviewed = await _scalar(
        session, select(func.count(func.distinct(AiInterview.session_id)))
    )
    saved_to_account = await _scalar(
        session,
        select(func.count()).select_from(Profile).where(Profile.user_id.isnot(None)),
    )

    # age-agnostic funnel: interests (A) → values (C, last block) → completed → enriched
    stages: list[tuple[str, int]] = [
        ("started", total),
        ("answered_interests", by_block.get("A", 0)),
        ("answered_values", by_block.get("C", 0)),
        ("completed", completed),
        ("enriched", enriched),
    ]
    funnel: list[dict] = []
    for idx, (name, cnt) in enumerate(stages):
        row: dict = {"stage": name, "count": cnt}
        if idx > 0:
            prev = stages[idx - 1][1]
            row["dropoff"] = prev - cnt if prev else 0
        funnel.append(row)

    # started/completed per age band
    age_rows = (
        await session.execute(
            select(
                Profile.age_band,
                func.count(),
                func.count().filter(S.status == "completed"),
            )
            .join(Profile, Profile.id == S.profile_id)
            .group_by(Profile.age_band)
        )
    ).all()
    by_age_band = {
        str(a): {"started": int(st), "completed": int(cp)} for a, st, cp in age_rows
    }

    # adults (working or 24+) vs teens
    adult_pred = (Profile.education_stage == "working") | (Profile.age_band == "24+")
    adult_started = await _scalar(
        session,
        select(func.count())
        .select_from(S)
        .join(Profile, Profile.id == S.profile_id)
        .where(adult_pred),
    )
    adult_completed = await _scalar(
        session,
        select(func.count())
        .select_from(S)
        .join(Profile, Profile.id == S.profile_id)
        .where(adult_pred, S.status == "completed"),
    )

    # match feedback: verdict counts + fit-rate per bucket (N2, our quality signal)
    MF = MatchFeedback
    fb_rows = (
        await session.execute(
            select(Match.bucket, MF.verdict, func.count())
            .join(
                Match,
                (Match.session_id == MF.session_id)
                & (Match.occupation_id == MF.occupation_id),
            )
            .group_by(Match.bucket, MF.verdict)
        )
    ).all()
    fb_by_verdict: dict[str, int] = {}
    fb_by_bucket: dict[str, dict[str, int]] = {}
    for bucket, verdict, c in fb_rows:
        fb_by_verdict[str(verdict)] = fb_by_verdict.get(str(verdict), 0) + int(c)
        b = fb_by_bucket.setdefault(str(bucket), {"fits": 0, "partial": 0, "not_me": 0})
        b[str(verdict)] = int(c)
    feedback = {
        "total": sum(fb_by_verdict.values()),
        "by_verdict": fb_by_verdict,
        "by_bucket": {b: {**v, "fit_rate": _fit_rate(v)} for b, v in fb_by_bucket.items()},
    }

    def _recent(days: int, col) -> object:
        return select(func.count()).select_from(S).where(col >= now - dt.timedelta(days=days))

    recent = {
        "started_7d": await _scalar(session, _recent(7, S.started_at)),
        "completed_7d": await _scalar(session, _recent(7, S.finished_at)),
        "started_30d": await _scalar(session, _recent(30, S.started_at)),
        "completed_30d": await _scalar(session, _recent(30, S.finished_at)),
    }

    return {
        "as_of": now.isoformat(),
        "totals": {
            "sessions": total,
            "completed": completed,
            "completion_rate": round(completed / total, 4) if total else 0.0,
            "abandoned": total - completed,
        },
        "by_status": by_status,
        "funnel": funnel,
        "post_result": {
            "enriched": enriched,
            "interview": interviewed,
            "shared": shared,
            "saved_to_account": saved_to_account,
        },
        "by_age_band": by_age_band,
        "feedback": feedback,
        "adults_vs_teens": {
            "adult": {"started": adult_started, "completed": adult_completed},
            "teen": {
                "started": total - adult_started,
                "completed": completed - adult_completed,
            },
        },
        "recent": recent,
    }
