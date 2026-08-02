"""Audit: split llm_calls tokens and record what each call would have cost

Revision ID: 0007_llm_call_cost
Revises: 0006_plan_items
Create Date: 2026-08-02

`tokens` alone can't answer "what does this feature cost" — input and output
price differently, and the subscription backend bills nothing at all while still
consuming real model capacity. Adds the input/output split plus the list-price
equivalent in USD x 10 000. Guarded per column, like the other incremental
migrations, so it is a no-op on a fresh DB where 0001_initial's create_all
already built the table.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_llm_call_cost"
down_revision: str | None = "0006_plan_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = ("input_tokens", "output_tokens", "cost_usd_x10000")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "llm_calls" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("llm_calls")}
    for name in _COLUMNS:
        if name not in existing:
            op.add_column("llm_calls", sa.Column(name, sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "llm_calls" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("llm_calls")}
    for name in _COLUMNS:
        if name in existing:
            op.drop_column("llm_calls", name)
