"""Declarative base + shared column helpers.

Conventions:
- UUID primary keys (server-generated) for anything user-facing or shareable.
- All timestamps are timezone-aware UTC, server-defaulted.
- PII is nullable and minimal (see PRIVACY_MODEL.md).
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )


def created_at_col() -> Mapped[dt.datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
