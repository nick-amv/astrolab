"""Monetization stubs (activated Wave 7, all payment code → adversarial-review)
and the analytics events table (no external trackers — DESIGN §10.1)."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    provider: Mapped[str | None] = mapped_column(String(32))
    external_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    amount_minor: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(24), default="pending")
    created_at: Mapped[dt.datetime] = created_at_col()


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plan: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default="inactive")
    current_period_end: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = created_at_col()


class Event(Base):
    """First-party funnel analytics. profile_id is nullable (pre-onboarding)."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(64), index=True)
    props: Mapped[dict | None] = mapped_column(JSON)
    ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
