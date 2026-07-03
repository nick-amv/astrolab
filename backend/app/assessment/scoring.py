"""Trait scoring from answers.

Blocks (question_bank.block):
- A = RIASEC activities. dimension ∈ R/I/A/S/E/C. Some carry a klimov_tag.
- B = school subjects. dimension = subject code. value = affinity (like×good).
- C = work values. v1: Likert, dimension = value axis. v2 (METHOD.md): forced-
  choice pairs, dimension = "axisA|axisB", value 1.0 = axisA chosen, 0.0 = axisB.

Answer value convention: 0.0 / 0.5 / 1.0 (no / meh / yes) for A and Likert C;
0..1 composite for B; 1.0/0.0 for forced-choice C.
"""

from __future__ import annotations

from dataclasses import dataclass

RIASEC_AXES = ("R", "I", "A", "S", "E", "C")
VALUE_AXES = (
    "achievement",
    "autonomy",
    "recognition",
    "relationships",
    "stability",
    "conditions",
)
KLIMOV_TYPES = ("human", "tech", "nature", "sign", "image")


@dataclass(frozen=True)
class AnswerItem:
    block: str
    dimension: str
    value: float
    klimov: str | None = None


def _mean_by(items: list[AnswerItem], keys: tuple[str, ...], attr: str = "dimension") -> dict:
    sums: dict[str, float] = dict.fromkeys(keys, 0.0)
    counts: dict[str, int] = dict.fromkeys(keys, 0)
    for it in items:
        key = getattr(it, attr)
        if key in sums:
            sums[key] += it.value
            counts[key] += 1
    return {k: round(sums[k] / counts[k], 4) if counts[k] else 0.0 for k in keys}


def _values_forced_choice(c_items: list[AnswerItem]) -> dict:
    """Win-rate per value axis from forced-choice pairs (dimension 'a|b',
    value 1.0 = a chosen, 0.0 = b chosen). Normalised to 0..1 per axis."""
    wins = dict.fromkeys(VALUE_AXES, 0.0)
    appear = dict.fromkeys(VALUE_AXES, 0)
    for x in c_items:
        a, _, b = x.dimension.partition("|")
        if a in appear:
            appear[a] += 1
            if x.value >= 0.5:
                wins[a] += 1
        if b in appear:
            appear[b] += 1
            if x.value < 0.5:
                wins[b] += 1
    return {k: round(wins[k] / appear[k], 4) if appear[k] else 0.0 for k in VALUE_AXES}


def compute_scores(answers: list[AnswerItem]) -> dict[str, dict]:
    """Return {riasec, klimov, values, subjects}, each a dict of axis→0..1."""
    a_items = [x for x in answers if x.block == "A"]
    b_items = [x for x in answers if x.block == "B"]
    c_items = [x for x in answers if x.block == "C"]

    riasec = _mean_by(a_items, RIASEC_AXES)

    klimov_items = [x for x in a_items if x.klimov]
    klimov = _mean_by(klimov_items, KLIMOV_TYPES, attr="klimov")

    # Forced-choice (v2) if any C item is a pair; else Likert (v1).
    if any("|" in x.dimension for x in c_items):
        values = _values_forced_choice(c_items)
    else:
        values = _mean_by(c_items, VALUE_AXES)

    subjects = {x.dimension: round(x.value, 4) for x in b_items}

    return {"riasec": riasec, "klimov": klimov, "values": values, "subjects": subjects}
