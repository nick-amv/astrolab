"""N2: match_feedback (user's reaction to a matched occupation)

Revision ID: 0005_match_feedback
Revises: 0004_widen_dimension
Create Date: 2026-07-05

One row per (session, occupation): fits | partial | not_me. Guarded, like the
other incremental migrations, so it is a no-op on a fresh DB where
0001_initial's create_all already built the table (keeps CI green).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_match_feedback"
down_revision: str | None = "0004_widen_dimension"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if "match_feedback" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "match_feedback",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("occupation_id", sa.Uuid(), nullable=False),
        sa.Column("verdict", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                  nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["assessment_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["occupation_id"], ["occupations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "occupation_id", name="uq_feedback_session_occ"),
    )
    op.create_index("ix_match_feedback_session_id", "match_feedback", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_match_feedback_session_id", table_name="match_feedback")
    op.drop_table("match_feedback")
