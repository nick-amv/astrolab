"""widen question_bank.dimension for forced-choice value pairs

Revision ID: 0004_widen_dimension
Revises: 0003_profile_cv
Create Date: 2026-07-03

A value pair encodes as "axisA|axisB" (e.g. "achievement|relationships" = 25
chars), which overflows the original varchar(24). Widen to 48.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_widen_dimension"
down_revision: str | None = "0003_profile_cv"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "question_bank",
        "dimension",
        type_=sa.String(48),
        existing_type=sa.String(24),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "question_bank",
        "dimension",
        type_=sa.String(24),
        existing_type=sa.String(48),
        existing_nullable=False,
    )
