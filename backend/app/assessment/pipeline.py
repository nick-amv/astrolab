"""Result pipeline: deterministic match → LLM re-rank/explain → store.

Runs once (at /score), so /result reads cached `matches` rows instead of
re-scoring or re-calling the LLM on every page load. The deterministic score and
`rank_det` are computed here and never change; the LLM only writes `rank_llm` +
`llm_reason`. Everything degrades cleanly if the LLM is unavailable.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment.ai import rerank_and_explain
from app.matching import Profile, match
from app.models import (
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

# How many bucketed candidates to hand the LLM (keeps the prompt small/fast).
LLM_CANDIDATES = 15


async def compute_and_store_matches(session: AsyncSession, ses: AssessmentSession) -> None:
    profile_row = (
        await session.execute(select(ProfileRow).where(ProfileRow.id == ses.profile_id))
    ).scalars().first()
    traits = (
        await session.execute(select(TraitScore).where(TraitScore.session_id == ses.id))
    ).scalars().all()
    by_kind = {t.kind: t.vector for t in traits}
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
    if not bucketed:
        await session.execute(delete(Match).where(Match.session_id == ses.id))
        await session.commit()
        return

    # occupation titles (ru) for the LLM prompt
    slugs = [s.occupation.slug for s in bucketed]
    occ_rows = (
        await session.execute(select(Occupation).where(Occupation.slug.in_(slugs)))
    ).scalars().all()
    id_by_slug = {o.slug: o.id for o in occ_rows}
    i18n = (
        await session.execute(
            select(OccupationI18n).where(
                OccupationI18n.occupation_id.in_([o.id for o in occ_rows]),
                OccupationI18n.locale == "ru",
            )
        )
    ).scalars().all()
    title_by = {str(r.occupation_id): r.title for r in i18n}

    candidates = [
        {
            "slug": s.occupation.slug,
            "title": title_by.get(str(id_by_slug.get(s.occupation.slug)), s.occupation.slug),
            "riasec": s.occupation.riasec,
        }
        for s in bucketed[:LLM_CANDIDATES]
    ]

    locale = profile_row.locale if profile_row else "ru"
    ai = await rerank_and_explain(
        {
            "riasec": by_kind.get("riasec", {}),
            "values": by_kind.get("values", {}),
            "subjects": by_kind.get("subjects", {}),
        },
        candidates,
        locale,
    )
    llm_order = {slug: i + 1 for i, slug in enumerate(ai["order"])} if ai else {}
    why = ai["why"] if ai else {}

    await session.execute(delete(Match).where(Match.session_id == ses.id))
    for det_rank, s in enumerate(bucketed, start=1):
        rank_llm = llm_order.get(s.occupation.slug)
        session.add(
            Match(
                session_id=ses.id,
                occupation_id=id_by_slug[s.occupation.slug],
                score=s.score,
                bucket=s.bucket,
                rank_det=det_rank,
                rank_llm=rank_llm,
                rank_final=rank_llm if rank_llm is not None else det_rank,
                llm_reason=why.get(s.occupation.slug),
            )
        )

    if ai:
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
