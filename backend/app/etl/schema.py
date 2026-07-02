"""Validated shapes for occupation drafts and review verdicts (JSON seeds)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LocalizedContent(BaseModel):
    title: str
    summary: str | None = None
    day_in_life: str | None = None
    who_fits: str | None = None


class CountryFact(BaseModel):
    country: str
    salary_low: int | None = None
    salary_high: int | None = None
    currency: str | None = None
    demand_note: str | None = None
    confidence: str = "estimate"  # facts default to estimate until sourced
    as_of_date: str | None = None  # ISO date


class OccupationDraft(BaseModel):
    slug: str
    esco_id: str | None = None
    onet_code: str | None = None
    field_tag: str | None = None
    edu_duration_band: str | None = None
    regulated: bool = False
    # RIASEC / values components 0..1. riasec_source records provenance.
    riasec: dict[str, float] = Field(default_factory=dict)
    riasec_source: str = "llm"  # onet | llm | curated
    values: dict[str, float] = Field(default_factory=dict)
    subjects: dict[str, float] = Field(default_factory=dict)  # subject_code -> weight
    i18n: dict[str, LocalizedContent] = Field(default_factory=dict)  # locale -> content
    facts: list[CountryFact] = Field(default_factory=list)


class ModelVote(BaseModel):
    model: str
    verdict: str  # approve | reject
    rationale: str | None = None


class ReviewVerdict(BaseModel):
    slug: str
    locale: str = "ru"
    verdict: str  # approved | rejected | split
    models: list[ModelVote] = Field(default_factory=list)
    factual_flags: list[str] = Field(default_factory=list)
