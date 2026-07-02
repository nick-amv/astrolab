"""Pure deterministic matching engine.

score = w_riasec · cos(riasec_u, riasec_o)
      + w_subjects · subject_fit
      + w_values  · cos(values_u, values_o)
      − soft_penalties

Weights come from a scoring_config `weights` dict (age-band aware). Buckets:
- core       — top ranks with score > core_tau
- near       — the next undervalued adjacents just below core
- dark_horse — strong on the user's single top RIASEC axis but not already
               surfaced; widens horizons (DESIGN §4.3).

Everything here is a pure function of its inputs — no DB, no clock, no LLM.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

RIASEC_AXES = ("R", "I", "A", "S", "E", "C")
VALUE_AXES = (
    "achievement",
    "autonomy",
    "recognition",
    "relationships",
    "stability",
    "conditions",
)


@dataclass(frozen=True)
class Profile:
    """A test-taker's computed vectors (each component 0..1)."""

    riasec: dict[str, float]
    values: dict[str, float] = field(default_factory=dict)
    subjects: dict[str, float] = field(default_factory=dict)  # subject_code -> affinity
    age_band: str = "17-19"
    # Soft constraints: e.g. {"max_edu_years": 4}. Absent = no penalty.
    constraints: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class OccupationVec:
    """The scoring-relevant projection of an occupation."""

    id: str
    slug: str
    riasec: dict[str, float]
    values: dict[str, float] = field(default_factory=dict)
    subjects: dict[str, float] = field(default_factory=dict)  # subject_code -> weight
    edu_years: float | None = None  # for the soft penalty
    field_tag: str | None = None  # coarse area, used only for dark-horse variety


@dataclass(frozen=True)
class ScoredOccupation:
    occupation: OccupationVec
    score: float
    rank_det: int
    bucket: str  # core | near | dark_horse | none


def cosine(a: dict[str, float], b: dict[str, float], axes: tuple[str, ...]) -> float:
    """Cosine similarity over a fixed axis set; 0 if either vector is empty."""
    va = [float(a.get(k, 0.0)) for k in axes]
    vb = [float(b.get(k, 0.0)) for k in axes]
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(x * x for x in vb))
    if na == 0.0 or nb == 0.0:
        return 0.0
    dot = sum(x * y for x, y in zip(va, vb, strict=True))
    return dot / (na * nb)


def subject_fit(user_subjects: dict[str, float], occ_subjects: dict[str, float]) -> float:
    """Weighted mean of the user's affinity over the occupation's key subjects.
    0 when the occupation lists no key subjects (neutral, not penalising)."""
    if not occ_subjects:
        return 0.0
    total_w = sum(occ_subjects.values())
    if total_w <= 0:
        return 0.0
    acc = sum(user_subjects.get(code, 0.0) * w for code, w in occ_subjects.items())
    return acc / total_w


def _weights_for(config: dict, age_band: str) -> dict[str, float]:
    by_band = (config or {}).get("by_age_band", {})
    if age_band in by_band:
        return by_band[age_band]
    return (config or {}).get("default", {"riasec": 0.5, "subjects": 0.25, "values": 0.25})


def _soft_penalty(profile: Profile, occ: OccupationVec) -> float:
    """Small, bounded penalties for stated constraints. Pushes down, never out."""
    penalty = 0.0
    max_years = profile.constraints.get("max_edu_years")
    if max_years is not None and occ.edu_years is not None and occ.edu_years > max_years:
        # 0.03 per extra year, capped at 0.15 — a nudge, not a veto.
        penalty += min(0.15, 0.03 * (occ.edu_years - max_years))
    return penalty


def score_occupation(profile: Profile, occ: OccupationVec, config: dict) -> float:
    w = _weights_for(config, profile.age_band)
    s = (
        w.get("riasec", 0.5) * cosine(profile.riasec, occ.riasec, RIASEC_AXES)
        + w.get("subjects", 0.25) * subject_fit(profile.subjects, occ.subjects)
        + w.get("values", 0.25) * cosine(profile.values, occ.values, VALUE_AXES)
    )
    return s - _soft_penalty(profile, occ)


def _top_user_axis(profile: Profile) -> str | None:
    if not profile.riasec:
        return None
    return max(RIASEC_AXES, key=lambda k: profile.riasec.get(k, 0.0))


def match(
    profile: Profile,
    occupations: list[OccupationVec],
    config: dict,
    *,
    core_size: int = 5,
    near_size: int = 5,
    dark_horse_size: int = 3,
) -> list[ScoredOccupation]:
    """Score, rank (deterministic), and bucket occupations. Stable ordering:
    by score desc, then slug asc — so equal scores never reorder run to run."""
    core_tau = float((config or {}).get("core_tau", 0.55))

    scored = [(occ, score_occupation(profile, occ, config)) for occ in occupations]
    scored.sort(key=lambda t: (-t[1], t[0].slug))

    results: list[ScoredOccupation] = []
    core_ids: set[str] = set()
    near_ids: set[str] = set()

    for i, (occ, s) in enumerate(scored):
        rank = i + 1
        bucket = "none"
        if rank <= core_size and s > core_tau:
            bucket = "core"
            core_ids.add(occ.id)
        results.append(ScoredOccupation(occupation=occ, score=s, rank_det=rank, bucket=bucket))

    # near = the next undervalued adjacents right below core, above zero.
    near_taken = 0
    for r in results:
        if near_taken >= near_size:
            break
        if r.bucket == "none" and r.score > 0:
            r_new = ScoredOccupation(r.occupation, r.score, r.rank_det, "near")
            results[r.rank_det - 1] = r_new
            near_ids.add(r.occupation.id)
            near_taken += 1

    # dark_horse = strong on the user's top axis, from a field not already in
    # core, not yet surfaced. Widens horizons.
    top_axis = _top_user_axis(profile)
    if top_axis:
        core_fields = {r.occupation.field_tag for r in results if r.bucket == "core"}
        candidates = [
            r
            for r in results
            if r.bucket == "none"
            and r.occupation.riasec.get(top_axis, 0.0) >= 0.7
            and r.occupation.field_tag not in core_fields
        ]
        candidates.sort(key=lambda r: (-r.occupation.riasec.get(top_axis, 0.0), r.occupation.slug))
        for r in candidates[:dark_horse_size]:
            results[r.rank_det - 1] = ScoredOccupation(
                r.occupation, r.score, r.rank_det, "dark_horse"
            )

    return results
