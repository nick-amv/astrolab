"""Result pipeline, split so the LLM never blocks the result (DESIGN §4.4).

- store_deterministic(): fast (~1s). Deterministic match → store `matches` with
  rank_det (= rank_final). Runs synchronously at /score.
- enrich_with_llm(): the LLM re-rank + "why you". Runs via a separate /enrich
  call the result page fires AFTER showing the deterministic result, so the user
  never waits on the shared Max-subscription CLI (which can queue for tens of
  seconds). Updates rank_llm / rank_final / llm_reason + writes the audit row.
  Fully degradable: on any failure the deterministic result stands.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment.ai import rerank_and_explain
from app.matching import Profile, match
from app.models import (
    AiInterview,
    AssessmentSession,
    LlmCall,
    Match,
    Occupation,
    OccupationI18n,
    ScoringConfig,
    TraitScore,
)
from app.models import Profile as ProfileRow
from app.services.catalog import load_published_vectors

LLM_CANDIDATES = 15


async def _profile_from_traits(session: AsyncSession, ses: AssessmentSession):
    traits = (
        await session.execute(select(TraitScore).where(TraitScore.session_id == ses.id))
    ).scalars().all()
    by_kind = {t.kind: t.vector for t in traits}
    profile_row = (
        await session.execute(select(ProfileRow).where(ProfileRow.id == ses.profile_id))
    ).scalars().first()
    return by_kind, profile_row


async def store_deterministic(session: AsyncSession, ses: AssessmentSession) -> None:
    by_kind, profile_row = await _profile_from_traits(session, ses)
    if not by_kind:
        return
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
    bucketed = [s for s in scored if s.bucket != "none"]

    await session.execute(delete(Match).where(Match.session_id == ses.id))
    for det_rank, s in enumerate(bucketed, start=1):
        session.add(
            Match(
                session_id=ses.id,
                occupation_id=uuid.UUID(s.occupation.id),
                score=s.score,
                bucket=s.bucket,
                rank_det=det_rank,
                rank_llm=None,
                rank_final=det_rank,
                llm_reason=None,
            )
        )
    await session.commit()


async def enrich_with_llm(session: AsyncSession, ses: AssessmentSession) -> bool:
    """Run the LLM re-rank/explain over the stored matches. Returns True if it
    applied. Idempotent-ish: re-running just re-writes the LLM fields."""
    by_kind, profile_row = await _profile_from_traits(session, ses)
    if not by_kind:
        return False
    matches = (
        await session.execute(
            select(Match).where(Match.session_id == ses.id).order_by(Match.rank_det)
        )
    ).scalars().all()
    if not matches:
        return False

    occ_rows = (
        await session.execute(
            select(Occupation).where(Occupation.id.in_([m.occupation_id for m in matches]))
        )
    ).scalars().all()
    occ_by_id = {o.id: o for o in occ_rows}
    i18n = (
        await session.execute(
            select(OccupationI18n).where(
                OccupationI18n.occupation_id.in_([o.id for o in occ_rows]),
                OccupationI18n.locale == "ru",
            )
        )
    ).scalars().all()
    title_by = {str(r.occupation_id): r.title for r in i18n}

    candidates = []
    slug_to_match = {}
    for m in matches[:LLM_CANDIDATES]:
        occ = occ_by_id.get(m.occupation_id)
        if occ is None:
            continue
        candidates.append(
            {
                "slug": occ.slug,
                "title": title_by.get(str(occ.id), occ.slug),
                "riasec": occ.riasec,
            }
        )
        slug_to_match[occ.slug] = (m, occ)

    interview_row = (
        await session.execute(select(AiInterview).where(AiInterview.session_id == ses.id))
    ).scalars().first()
    interview = (interview_row.transcript or {}).get("items") if interview_row else None

    locale = profile_row.locale if profile_row else "ru"
    cv = profile_row.cv if profile_row else None
    ai = await rerank_and_explain(
        {k: by_kind.get(k, {}) for k in ("riasec", "values", "subjects")},
        candidates,
        locale,
        interview,
        cv,
    )
    if not ai:
        return False

    llm_order = {slug: i + 1 for i, slug in enumerate(ai["order"])}
    why = ai["why"]
    for slug, (m, _occ) in slug_to_match.items():
        rank_llm = llm_order.get(slug)
        if rank_llm is not None:
            m.rank_llm = rank_llm
            m.rank_final = rank_llm
        m.llm_reason = why.get(slug)

    session.add(
        LlmCall(
            session_id=ses.id,
            purpose="rerank",
            backend=ai["audit"]["backend"],
            model=ai["audit"]["model"],
            prompt_hash=ai["audit"]["prompt_hash"],
            config_version=ses.scoring_version,
            output={"order": ai["order"], "why_count": len(why)},
            tokens=ai["audit"]["tokens"],
            latency_ms=ai["audit"]["latency_ms"],
        )
    )
    await session.commit()
    return True
