"""Deterministic occupation matching (DESIGN §4.3).

This package is pure and reproducible: given the same profile, occupations, and
scoring_config, it returns the same scores and ranks. The LLM never enters here
(it re-ranks a separate `rank_llm` layer downstream). Wave 2 ships the engine +
a preview API; wiring real assessment profiles in is Wave 1/3.
"""

from app.matching.engine import (
    OccupationVec,
    Profile,
    ScoredOccupation,
    match,
)

__all__ = ["Profile", "OccupationVec", "ScoredOccupation", "match"]
