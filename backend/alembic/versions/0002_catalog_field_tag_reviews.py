"""wave 2: occupations.field_tag + content_reviews

Revision ID: 0002_catalog
Revises: 0001_initial
Create Date: 2026-07-02

Incremental (op.* steps, not create_all): add the coarse `field_tag` used for
dark-horse matching variety, and the `content_reviews` audit table for the
multi-model publication gate (DATA_SOURCES §6).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_catalog"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("occupations", sa.Column("field_tag", sa.String(length=32), nullable=True))
    op.create_index("ix_occupations_field_tag", "occupations", ["field_tag"])

    op.create_table(
        "content_reviews",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("occupation_id", sa.Uuid(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("models", sa.JSON(), nullable=False),
        sa.Column("factual_flags", sa.JSON(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                  nullable=False),
        sa.ForeignKeyConstraint(["occupation_id"], ["occupations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_content_reviews_occupation_id", "content_reviews", ["occupation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_content_reviews_occupation_id", table_name="content_reviews")
    op.drop_table("content_reviews")
    op.drop_index("ix_occupations_field_tag", table_name="occupations")
    op.drop_column("occupations", "field_tag")
