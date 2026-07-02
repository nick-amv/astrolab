"""Match results, AI interview transcripts, LLM audit trail, and share reports.

Determinism boundary (acceptance gate, Wave 3): `matches.score` and `rank_det`
come ONLY from the deterministic scorer. The LLM re-rank writes `rank_llm`
separately; `rank_final = rank_llm if llm_status == 'ok' else rank_det` is
computed on the backend so the UI never hardcodes the rule. Every LLM call is
logged in `llm_calls` (prompt_hash, model, config_version, output).
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"), index=True
    )
    occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE")
    )
    score: Mapped[float] = mapped_column(Float)  # deterministic score, reproducible
    bucket: Mapped[str] = mapped_column(String(16))  # core | near | darkhorse
    rank_det: Mapped[int] = mapped_column(Integer)  # rank from deterministic score
    rank_llm: Mapped[int | None] = mapped_column(Integer)  # after LLM re-rank, if any
    rank_final: Mapped[int] = mapped_column(Integer)  # backend-computed display rank
    llm_reason: Mapped[str | None] = mapped_column(String)  # "why you" text, if generated


class AiInterview(Base):
    """Lives and dies with its session (PRIVACY_MODEL.md: transcripts are not
    retained beyond the session's retention window)."""

    __tablename__ = "ai_interviews"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"), index=True
    )
    transcript: Mapped[dict | None] = mapped_column(JSON)
    summary: Mapped[dict | None] = mapped_column(JSON)
    model: Mapped[str | None] = mapped_column(String(48))
    tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = created_at_col()


class LlmCall(Base):
    """Audit trail for every LLM invocation — reproducibility + cost + abuse."""

    __tablename__ = "llm_calls"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="SET NULL"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(32))  # interview | rerank | translate | ...
    backend: Mapped[str | None] = mapped_column(String(16))  # max_cli | openrouter
    model: Mapped[str | None] = mapped_column(String(48))
    prompt_hash: Mapped[str | None] = mapped_column(String(64))
    config_version: Mapped[int | None] = mapped_column(Integer)
    output: Mapped[dict | None] = mapped_column(JSON)
    tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    ts: Mapped[dt.datetime] = created_at_col()


class Report(Base):
    """Shareable result at /r/<token>. Only the hash is stored; links expire."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))  # teen | parent | adult
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    pdf_path: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[dt.datetime] = created_at_col()
