"""N4: plan_items (saved 'try it this week' steps a user checks off)

Revision ID: 0006_plan_items
Revises: 0005_match_feedback
Create Date: 2026-07-05

One row per (user, occupation, step); `done` toggles. Guarded, like the other
incremental migrations, so it is a no-op on a fresh DB where 0001_initial's
create_all already built the table (keeps CI green).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_plan_items"
down_revision: str | None = "0005_match_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if "plan_items" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "plan_items",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("occupation_slug", sa.String(length=80), nullable=False),
        sa.Column("step_idx", sa.Integer(), nullable=False),
        sa.Column("audience", sa.String(length=8), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                  nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "occupation_slug", "step_idx", name="uq_plan_user_occ_step"),
    )
    op.create_index("ix_plan_items_user_id", "plan_items", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_plan_items_user_id", table_name="plan_items")
    op.drop_table("plan_items")
