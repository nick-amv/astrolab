"""Assessment scoring (METHOD.md §3). Turns raw answers into trait vectors.

Pure and reproducible: same answers + same question_bank_version → same
vectors. No LLM, no clock. Version 1 uses Likert value items (agree/neutral/no)
rather than forced-choice pairs; that is a documented v1 choice (METHOD §4.5),
calibrated toward forced-choice in a later version.
"""

from app.assessment.scoring import AnswerItem, compute_scores

__all__ = ["AnswerItem", "compute_scores"]
