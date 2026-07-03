"""Optional mini-interview: a few reflective statements chosen from the test
profile (the user's two strongest RIASEC axes, plus universal work-style probes).

The statements are a static, versioned asset (seed/interview_v1.json) — no DB
seeding. Answers are stored in ai_interviews.transcript and fed into the LLM
enrich so the "why you" text can reference how the person actually reflected.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_SEED = Path(__file__).resolve().parent.parent.parent / "seed" / "interview_v1.json"
RIASEC_AXES = ("R", "I", "A", "S", "E", "C")


@lru_cache(maxsize=1)
def _statements() -> list[dict]:
    data = json.loads(_SEED.read_text("utf-8"))
    # attach a stable id = index in the full list
    return [{"id": str(i), **s} for i, s in enumerate(data["statements"])]


def interview_version() -> int:
    return int(json.loads(_SEED.read_text("utf-8")).get("version", 1))


def select_statements(riasec: dict, limit: int = 6) -> list[dict]:
    """Two statements for each of the top-2 axes + universal probes, up to limit."""
    stmts = _statements()
    top2 = [a for a, _ in sorted(riasec.items(), key=lambda kv: -kv[1])[:2] if a in RIASEC_AXES]
    picked: list[dict] = []
    for axis in top2:
        picked.extend(s for s in stmts if s["axis"] == axis)
    universals = [s for s in stmts if s["axis"] == "universal"]
    # fill up to limit with universals
    for s in universals:
        if len(picked) >= limit:
            break
        picked.append(s)
    picked = picked[:limit]
    return [{"id": s["id"], "text": s["ru"]} for s in picked]


def text_for(statement_id: str) -> str | None:
    for s in _statements():
        if s["id"] == statement_id:
            return str(s["ru"])
    return None
