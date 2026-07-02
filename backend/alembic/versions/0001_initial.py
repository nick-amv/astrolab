"""initial schema (full §10.2 contracts + immutability trigger + seeds)

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-02

The whole DESIGN §10.2 contract lands in one migration (a design decision,
P7): no "we'll add the schema later" on tables that will hold people's results.
Tables are created straight from the ORM metadata so migration and models can
never drift for the initial revision; later waves add incremental op.* steps.

Two guarantees are enforced at the DB level here:
- scoring_config is immutable: a trigger rejects UPDATE and DELETE, so a
  historical result can never be silently re-scored.
- pgcrypto is enabled for server-side gen_random_uuid().
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.models import Base

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_IMMUTABLE_FN = """
CREATE OR REPLACE FUNCTION astrolab_block_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'row is immutable (table %)', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;
"""

_IMMUTABLE_TRIGGER = """
CREATE TRIGGER scoring_config_immutable
BEFORE UPDATE OR DELETE ON scoring_config
FOR EACH ROW EXECUTE FUNCTION astrolab_block_mutation();
"""

# Deterministic-scorer prior (DESIGN §4.3). Documented prior, NOT a validity
# claim; calibrated against real data once ~500 completions exist (METHOD.md).
_SCORING_V1 = {
    "default": {"riasec": 0.50, "subjects": 0.25, "values": 0.25},
    "by_age_band": {
        "14-16": {"riasec": 0.45, "subjects": 0.35, "values": 0.20},
        "17-19": {"riasec": 0.50, "subjects": 0.25, "values": 0.25},
        "20-23": {"riasec": 0.50, "subjects": 0.20, "values": 0.30},
        "24+": {"riasec": 0.45, "subjects": 0.15, "values": 0.40},
    },
    "core_tau": 0.55,
}

_DATA_SOURCES = [
    ("ESCO", "ESCO — free reuse with attribution", "https://esco.ec.europa.eu"),
    ("O*NET", "O*NET — public domain (with attribution)", "https://www.onetonline.org"),
    ("RU-classifiers", "Official open data (OKSO / admission rules)", None),
    ("manual-seed", "Manually curated by the Astrolab team", None),
    ("llm-estimate", "LLM-generated estimate — NOT a verified fact", None),
]


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    Base.metadata.create_all(bind=bind)

    op.execute(_IMMUTABLE_FN)
    op.execute(_IMMUTABLE_TRIGGER)

    scoring = sa.table(
        "scoring_config",
        sa.column("version", sa.Integer),
        sa.column("weights", sa.JSON),
        sa.column("note", sa.String),
    )
    op.bulk_insert(
        scoring,
        [{"version": 1, "weights": _SCORING_V1, "note": "seed prior; pre-calibration"}],
    )

    data_sources = sa.table(
        "data_sources",
        sa.column("name", sa.String),
        sa.column("license", sa.String),
        sa.column("url", sa.String),
    )
    op.bulk_insert(
        data_sources,
        [{"name": n, "license": lic, "url": url} for (n, lic, url) in _DATA_SOURCES],
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute("DROP TRIGGER IF EXISTS scoring_config_immutable ON scoring_config;")
    op.execute("DROP FUNCTION IF EXISTS astrolab_block_mutation();")
    Base.metadata.drop_all(bind=bind)
