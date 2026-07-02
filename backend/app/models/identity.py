"""Identity, consent, and deletion audit.

PII is minimal and optional: a result is fully usable with no account. When an
account exists it holds at most an email OR a tg_id — never a name. Tokens are
stored hashed, never raw (PRIVACY_MODEL.md).
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    tg_id: Mapped[int | None] = mapped_column(unique=True)
    created_at: Mapped[dt.datetime] = created_at_col()


class AuthToken(Base):
    """Magic-link / session tokens. Only the SHA-256 hash is stored."""

    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32))  # magic_link | session | tg
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[dt.datetime] = created_at_col()


class ConsentRecord(Base):
    """Parental / data-processing consent events (152-FZ / GDPR)."""

    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(48))  # parental | data_processing | ...
    granted_at: Mapped[dt.datetime] = created_at_col()

    __table_args__ = (UniqueConstraint("user_id", "kind", name="uq_consent_user_kind"),)


class DeletionLog(Base):
    """Right-to-erasure audit. subject_ref = anon_token or user id, hashed if PII."""

    __tablename__ = "deletion_log"

    id: Mapped[uuid.UUID] = uuid_pk()
    subject_ref: Mapped[str] = mapped_column(String(128), index=True)
    requested_at: Mapped[dt.datetime] = created_at_col()
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
