"""Metadata coverage — every §10.2 contract table exists in Base.metadata.

Runs without a database. Guards against a model being dropped from the initial
contract (acceptance gate: the schema is complete from commit one).
"""

from __future__ import annotations

from app.models import Base

EXPECTED_TABLES = {
    "users",
    "auth_tokens",
    "consent_records",
    "deletion_log",
    "profiles",
    "assessment_sessions",
    "question_bank",
    "question_i18n",
    "answers",
    "trait_scores",
    "scoring_config",
    "occupations",
    "occupation_i18n",
    "occupation_country",
    "occupation_subjects",
    "skills",
    "skill_i18n",
    "occupation_skills",
    "data_sources",
    "edu_domains",
    "edu_requirements",
    "occupation_edu",
    "milestones",
    "content_reviews",
    "matches",
    "ai_interviews",
    "llm_calls",
    "reports",
    "payments",
    "subscriptions",
    "events",
}


def test_all_contract_tables_present() -> None:
    actual = set(Base.metadata.tables.keys())
    missing = EXPECTED_TABLES - actual
    assert not missing, f"missing contract tables: {missing}"


def test_tokens_are_hashed_columns() -> None:
    # Privacy invariant: token columns are named *_hash, never a raw token.
    auth = Base.metadata.tables["auth_tokens"]
    reports = Base.metadata.tables["reports"]
    assert "token_hash" in auth.columns
    assert "token_hash" in reports.columns
    assert "token" not in auth.columns
    assert "expires_at" in reports.columns


def test_matches_has_split_ranks() -> None:
    # Determinism boundary: deterministic and LLM ranks are separate columns.
    m = Base.metadata.tables["matches"]
    for col in ("score", "rank_det", "rank_llm", "rank_final"):
        assert col in m.columns
