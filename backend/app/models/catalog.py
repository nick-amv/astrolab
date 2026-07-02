"""Occupation catalog + skills graph + education mapping + data provenance.

Provenance is a first-class concern (acceptance gate, Wave 2): every
fact-bearing field (salary, demand, requirements) carries a source_id,
confidence, and as_of_date. Nothing is published to the public catalog / SEO
until `occupations.published` is set by a human reviewer.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class DataSource(Base):
    """Provenance registry — ESCO, O*NET, RU classifiers, manual seeds, LLM."""

    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(64), unique=True)
    license: Mapped[str | None] = mapped_column(String(128))
    url: Mapped[str | None] = mapped_column(String)
    imported_at: Mapped[dt.datetime] = created_at_col()


class Occupation(Base):
    __tablename__ = "occupations"

    id: Mapped[uuid.UUID] = uuid_pk()
    esco_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    onet_code: Mapped[str | None] = mapped_column(String(16))
    riasec: Mapped[dict | None] = mapped_column(JSON)
    riasec_source: Mapped[str | None] = mapped_column(String(8))  # onet | llm | curated
    values: Mapped[dict | None] = mapped_column(JSON)
    edu_duration_band: Mapped[str | None] = mapped_column(String(16))
    regulated: Mapped[bool] = mapped_column(Boolean, default=False)
    slug: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    # Coarse area (e.g. tech, health, arts) — used for dark-horse variety in
    # matching and for catalog grouping.
    field_tag: Mapped[str | None] = mapped_column(String(32), index=True)
    # Only council-reviewed rows go to the public catalog / SEO (Wave 2 gate).
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class OccupationI18n(Base):
    __tablename__ = "occupation_i18n"

    id: Mapped[uuid.UUID] = uuid_pk()
    occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True
    )
    locale: Mapped[str] = mapped_column(String(8))
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str | None] = mapped_column(String)
    day_in_life: Mapped[str | None] = mapped_column(String)
    who_fits: Mapped[str | None] = mapped_column(String)
    content_source: Mapped[str | None] = mapped_column(String(16))  # esco | llm | human
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("occupation_id", "locale", name="uq_occ_locale"),)


class OccupationCountry(Base):
    """Salary / demand facts, per country. Always carries provenance."""

    __tablename__ = "occupation_country"

    id: Mapped[uuid.UUID] = uuid_pk()
    occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True
    )
    country: Mapped[str] = mapped_column(String(2))
    salary_low: Mapped[int | None] = mapped_column(Integer)
    salary_high: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(3))
    demand_note: Mapped[str | None] = mapped_column(String)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL")
    )
    confidence: Mapped[str | None] = mapped_column(String(8))  # high | medium | estimate
    as_of_date: Mapped[dt.date | None] = mapped_column(Date)
    reviewed_by: Mapped[str | None] = mapped_column(String(64))
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("occupation_id", "country", name="uq_occ_country"),)


class OccupationSubject(Base):
    __tablename__ = "occupation_subjects"

    id: Mapped[uuid.UUID] = uuid_pk()
    occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True
    )
    subject_code: Mapped[str] = mapped_column(String(32))
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    __table_args__ = (UniqueConstraint("occupation_id", "subject_code", name="uq_occ_subject"),)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = uuid_pk()
    esco_skill_id: Mapped[str | None] = mapped_column(String(64), unique=True)


class SkillI18n(Base):
    __tablename__ = "skill_i18n"

    id: Mapped[uuid.UUID] = uuid_pk()
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), index=True
    )
    locale: Mapped[str] = mapped_column(String(8))
    label: Mapped[str] = mapped_column(String(160))

    __table_args__ = (UniqueConstraint("skill_id", "locale", name="uq_skill_locale"),)


class OccupationSkill(Base):
    """Normalized M2M (not a jsonb blob) so the skill graph is queryable for
    'nearby' occupations and adult skill-transfer."""

    __tablename__ = "occupation_skills"

    occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class EduDomain(Base):
    """A field of study / degree track. RU: OKSO code."""

    __tablename__ = "edu_domains"

    id: Mapped[uuid.UUID] = uuid_pk()
    country: Mapped[str] = mapped_column(String(2), index=True)
    code: Mapped[str] = mapped_column(String(32))
    title_key: Mapped[str] = mapped_column(String(96))

    __table_args__ = (UniqueConstraint("country", "code", name="uq_edu_domain_country_code"),)


class EduRequirement(Base):
    __tablename__ = "edu_requirements"

    id: Mapped[uuid.UUID] = uuid_pk()
    domain_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("edu_domains.id", ondelete="CASCADE"), index=True
    )
    data: Mapped[dict] = mapped_column(JSON)  # e.g. {"ege_combos": [["math","rus","phys"]]}


class OccupationEdu(Base):
    __tablename__ = "occupation_edu"

    occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), primary_key=True
    )
    domain_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("edu_domains.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class Milestone(Base):
    """Admission deadlines, e.g. 'choose EGE subjects by Feb 1'."""

    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = uuid_pk()
    country: Mapped[str] = mapped_column(String(2), index=True)
    education_stage: Mapped[str] = mapped_column(String(32))
    date_rule: Mapped[str] = mapped_column(String(64))  # e.g. "02-01" or "relative:-120d"
    title_key: Mapped[str] = mapped_column(String(96))


class ContentReview(Base):
    """Multi-model review verdict for an occupation's descriptive content
    (DATA_SOURCES §6). Publication requires a passing verdict; the per-model
    rationale is retained for audit."""

    __tablename__ = "content_reviews"

    id: Mapped[uuid.UUID] = uuid_pk()
    occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True
    )
    locale: Mapped[str] = mapped_column(String(8))
    verdict: Mapped[str] = mapped_column(String(16))  # approved | rejected | split
    models: Mapped[dict] = mapped_column(JSON)  # [{model, verdict, rationale}]
    factual_flags: Mapped[dict | None] = mapped_column(JSON)
    reviewed_at: Mapped[dt.datetime] = created_at_col()
