"""Assessment core: profiles, sessions, the versioned question bank, answers,
computed trait scores, and the immutable scoring config.

Two reproducibility guarantees live here (acceptance gate, Wave 1):
- `scoring_config` rows are immutable (a DB trigger blocks UPDATE/DELETE — see
  the initial migration). New weights = a new version row.
- Every session pins the exact `question_bank_version` + `scoring_version` it
  ran under, so a result can always be recomputed identically.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Profile(Base):
    """A test-taker. Works fully anonymously: user_id is null until claimed."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    anon_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    age_band: Mapped[str] = mapped_column(String(8))  # 14-16 | 17-19 | 20-23 | 24+
    locale: Mapped[str] = mapped_column(String(8), default="ru")
    country_live: Mapped[str | None] = mapped_column(String(2))
    country_study: Mapped[str | None] = mapped_column(String(2))
    education_stage: Mapped[str | None] = mapped_column(String(32))
    # Adult flow (Wave 5): LLM-extracted CV context {summary, skills[], field}.
    cv: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = created_at_col()


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    question_bank_version: Mapped[int] = mapped_column(Integer)
    scoring_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="started")  # started|partial|done
    started_at: Mapped[dt.datetime] = created_at_col()
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class QuestionBank(Base):
    """One row per (item, version). Rows are treated as immutable snapshots;
    a new item wording = a new version, never an in-place edit of the text.
    Only `active` may be toggled to retire a version."""

    __tablename__ = "question_bank"

    id: Mapped[uuid.UUID] = uuid_pk()
    block: Mapped[str] = mapped_column(String(8))  # A | B | C | D
    dimension: Mapped[str] = mapped_column(String(24))  # R/I/A/S/E/C, value axis, subject...
    klimov_tag: Mapped[str | None] = mapped_column(String(24))
    version: Mapped[int] = mapped_column(Integer, index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class QuestionI18n(Base):
    __tablename__ = "question_i18n"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_bank.id", ondelete="CASCADE"), index=True
    )
    locale: Mapped[str] = mapped_column(String(8))
    text: Mapped[str] = mapped_column(String)
    media: Mapped[str | None] = mapped_column(String)

    __table_args__ = (UniqueConstraint("question_id", "locale", name="uq_question_locale"),)


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_bank.id", ondelete="RESTRICT")
    )
    value: Mapped[float] = mapped_column(Float)
    answered_at: Mapped[dt.datetime] = created_at_col()

    __table_args__ = (UniqueConstraint("session_id", "question_id", name="uq_answer_session_q"),)


class TraitScore(Base):
    """Per-session computed vectors: riasec | klimov | values | tipi | subjects."""

    __tablename__ = "trait_scores"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    vector: Mapped[dict] = mapped_column(JSON)
    computed_at: Mapped[dt.datetime] = created_at_col()

    __table_args__ = (UniqueConstraint("session_id", "kind", name="uq_trait_session_kind"),)


class ScoringConfig(Base):
    """Immutable. version is the PK; a new weighting is a new row. A DB trigger
    (initial migration) rejects UPDATE and DELETE so a historical result is
    never silently re-scored."""

    __tablename__ = "scoring_config"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    weights: Mapped[dict] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
