"""wave 5: profiles.cv (adult CV context)

Revision ID: 0003_profile_cv
Revises: 0002_catalog
Create Date: 2026-07-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_profile_cv"
down_revision: str | None = "0002_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Guard: 0001_initial's create_all already adds `cv` on a fresh DB (CI), so
    # only add it on databases created before this revision (keeps CI green
    # without re-running on prod, which is already past this migration).
    insp = sa.inspect(op.get_bind())
    if "cv" not in {c["name"] for c in insp.get_columns("profiles")}:
        op.add_column("profiles", sa.Column("cv", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "cv")
