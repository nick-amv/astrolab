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

import structlog

from app.llm import LLMRequest, LLMUnavailable, get_provider

_log = structlog.get_logger("astrolab.interview")

_SEED = Path(__file__).resolve().parent.parent.parent / "seed" / "interview_v1.json"
RIASEC_AXES = ("R", "I", "A", "S", "E", "C")

_AXIS = {
    "R": "Realistic",
    "I": "Investigative",
    "A": "Artistic",
    "S": "Social",
    "E": "Enterprising",
    "C": "Conventional",
}
_LANG = {"ru": "Russian", "en": "English", "de": "German", "es": "Spanish", "fr": "French"}

_GEN_SYSTEM = (
    "You are a warm, honest career-guidance mentor for teenagers and adults. "
    "Given a person's interest profile (RIASEC model), work values and favourite "
    "school subjects, write short FIRST-PERSON reflective statements the person "
    "will rate on a 'that's me / partly / not me' scale. Purpose: sharpen their "
    "sense of direction — surface tensions in the profile, test standout traits, "
    "probe work-style. Rules: exactly 5-6 statements; each a single first-person "
    "sentence; concrete and kind; NOT yes/no questions; no cliches. STRICT JSON only."
)


def _profile_digest(profile: dict) -> str:
    riasec = profile.get("riasec", {})
    top = ", ".join(
        f"{_AXIS.get(k, k)} ({v:.2f})"
        for k, v in sorted(riasec.items(), key=lambda kv: -kv[1])[:3]
        if v > 0
    )
    values = profile.get("values", {})
    tv = ", ".join(k for k, v in sorted(values.items(), key=lambda kv: -kv[1])[:3] if v > 0)
    subjects = profile.get("subjects", {})
    ts = ", ".join(k for k, v in sorted(subjects.items(), key=lambda kv: -kv[1])[:4] if v > 0)
    return (
        f"Strongest interests (RIASEC): {top or 'n/a'}. "
        f"Top values: {tv or 'n/a'}. Favourite subjects: {ts or 'n/a'}."
    )


async def generate_statements(profile: dict, locale: str, limit: int = 6) -> list[dict] | None:
    """LLM-personalised reflective statements for THIS profile. Degradable:
    returns None on any failure so the caller falls back to the static set."""
    lang = _LANG.get(locale, "English")
    user = (
        f"{_profile_digest(profile)}\n\n"
        f"Write 5-6 reflective statements addressed to this specific person, in {lang}. "
        'Reply strictly as JSON: {"statements": ["...", "..."]}'
    )
    req = LLMRequest(
        feature="interview",
        model=None,
        system_prompt=_GEN_SYSTEM,
        user_prompt=user,
        locale=locale,
        max_tokens=700,
        temperature=0.5,
        timeout_s=30,  # blocking page load; degrade to static set if slow
    )
    try:
        res = await get_provider().complete_json(req)
    except LLMUnavailable as exc:
        _log.info("interview.gen.unavailable", error=str(exc))
        return None
    try:
        data = json.loads(res.text)
        items = [str(s).strip() for s in data.get("statements", []) if str(s).strip()]
    except Exception as exc:  # noqa: BLE001 — bad output degrades to static set
        _log.warning("interview.gen.bad_output", error=str(exc))
        return None
    items = items[:limit]
    if len(items) < 3:
        return None
    return [{"id": f"g{i}", "text": t} for i, t in enumerate(items)]


@lru_cache(maxsize=1)
def _statements() -> list[dict]:
    data = json.loads(_SEED.read_text("utf-8"))
    # attach a stable id = index in the full list
    return [{"id": str(i), **s} for i, s in enumerate(data["statements"])]


def interview_version() -> int:
    return int(json.loads(_SEED.read_text("utf-8")).get("version", 1))


def _localized(statement: dict, locale: str) -> str:
    """Statement text in the requested locale, falling back to Russian."""
    return str(statement.get(locale) or statement["ru"])


def select_statements(riasec: dict, limit: int = 6, locale: str = "ru") -> list[dict]:
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
    return [{"id": s["id"], "text": _localized(s, locale)} for s in picked]


def text_for(statement_id: str, locale: str = "ru") -> str | None:
    for s in _statements():
        if s["id"] == statement_id:
            return _localized(s, locale)
    return None
