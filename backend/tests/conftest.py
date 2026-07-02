"""Shared fixtures. DB-backed tests run only when RUN_DB_TESTS=1 (set in CI,
where a Postgres service + `alembic upgrade head` have already run)."""

from __future__ import annotations

import os

import pytest

RUN_DB = os.environ.get("RUN_DB_TESTS") == "1"

requires_db = pytest.mark.skipif(not RUN_DB, reason="RUN_DB_TESTS!=1 (no Postgres)")
