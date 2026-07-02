"""Matching preview API.

Runs the deterministic engine over the published catalog for a supplied profile
vector, returning ranked buckets. This exercises the Wave 2 engine end to end
without the assessment UI; Wave 1/3 will feed real trait vectors from a session.
The LLM re-rank layer is not involved here (that is rank_llm, downstream).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.matching import Profile, match
from app.models import ScoringConfig
from app.services.catalog import load_published_vectors

router = APIRouter(prefix="/api/match", tags=["match"])


class ProfileIn(BaseModel):
    riasec: dict[str, float] = Field(default_factory=dict)
    values: dict[str, float] = Field(default_factory=dict)
    subjects: dict[str, float] = Field(default_factory=dict)
    age_band: str = "17-19"
    constraints: dict[str, float] = Field(default_factory=dict)


class MatchItem(BaseModel):
    slug: str
    score: float
    rank_det: int
    bucket: str


class MatchPreviewOut(BaseModel):
    scoring_version: int | None
    core: list[MatchItem]
    near: list[MatchItem]
    dark_horse: list[MatchItem]


@router.post("/preview", response_model=MatchPreviewOut)
async def preview(
    body: ProfileIn,
    session: AsyncSession = Depends(get_session),
) -> MatchPreviewOut:
    cfg_row = (
        await session.execute(select(ScoringConfig).order_by(ScoringConfig.version.desc()))
    ).scalars().first()
    config = cfg_row.weights if cfg_row else {}

    vectors = await load_published_vectors(session)
    profile = Profile(
        riasec=body.riasec,
        values=body.values,
        subjects=body.subjects,
        age_band=body.age_band,
        constraints=body.constraints,
    )
    scored = match(profile, vectors, config)

    def to_items(bucket: str) -> list[MatchItem]:
        return [
            MatchItem(
                slug=s.occupation.slug, score=round(s.score, 4),
                rank_det=s.rank_det, bucket=s.bucket,
            )
            for s in scored
            if s.bucket == bucket
        ]

    return MatchPreviewOut(
        scoring_version=cfg_row.version if cfg_row else None,
        core=to_items("core"),
        near=to_items("near"),
        dark_horse=to_items("dark_horse"),
    )
