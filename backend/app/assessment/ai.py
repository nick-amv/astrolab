"""LLM re-rank + "why you" (DESIGN §4.3, a design decision P3).

One call: given the deterministic top-N occupations for a profile, the LLM
reorders THEM (never introduces an occupation outside the set — anti-
hallucination) and writes a short, warm, concrete "why this fits you" for each,
on the user's language.

Degradable: any failure returns None and the caller keeps the deterministic
order with no LLM text. The deterministic score is never touched (that stays
rank_det); the LLM only produces rank_llm + explanations.
"""

from __future__ import annotations

import hashlib
import json

import structlog

from app.llm import LLMRequest, LLMUnavailable, get_provider

_log = structlog.get_logger("astrolab.ai")

# RIASEC axis names in English; the LLM writes its output in the user's
# language (see the directive in build_prompt). Prompts stay locale-agnostic so
# adding a language needs no code change and the cyrillic-in-source lint passes.
_AXIS = {
    "R": "Realistic",
    "I": "Investigative",
    "A": "Artistic",
    "S": "Social",
    "E": "Enterprising",
    "C": "Conventional",
}

_LANG = {"ru": "Russian", "en": "English", "de": "German", "es": "Spanish"}

_SYSTEM = (
    "You are a warm, honest career-guidance mentor for teenagers and adults. "
    "Given a person's interest profile (RIASEC model), work values, and favourite "
    "school subjects, explain why specific occupations fit THIS person. "
    "Rules: 1-2 short sentences per occupation; concrete and kind; no cliches, no "
    "promises of wealth, no pressure; never invent occupations outside the given "
    "list. Return STRICT JSON only."
)


def _profile_summary(profile: dict) -> str:
    riasec = profile.get("riasec", {})
    top = sorted(riasec.items(), key=lambda kv: -kv[1])[:3]
    top_txt = ", ".join(f"{_AXIS.get(k, k)} ({v:.2f})" for k, v in top if v > 0)
    values = profile.get("values", {})
    top_vals = ", ".join(k for k, v in sorted(values.items(), key=lambda kv: -kv[1])[:3] if v > 0)
    subjects = profile.get("subjects", {})
    top_subj = ", ".join(k for k, v in sorted(subjects.items(), key=lambda kv: -kv[1])[:4] if v > 0)
    return (
        f"RIASEC profile (strongest): {top_txt or 'n/a'}. "
        f"Values: {top_vals or 'n/a'}. "
        f"Favourite subjects: {top_subj or 'n/a'}."
    )


def build_prompt(profile: dict, occupations: list[dict], locale: str) -> tuple[str, str]:
    lines = [
        f"- {o['slug']}: {o['title']} (RIASEC "
        + ", ".join(f"{k}{v:.1f}" for k, v in (o.get("riasec") or {}).items())
        + ")"
        for o in occupations
    ]
    lang = _LANG.get(locale, "English")
    user = (
        f"{_profile_summary(profile)}\n\n"
        "Candidate occupations (only from this list, do not add any):\n"
        + "\n".join(lines)
        + "\n\nSort them by how well they fit THIS specific person, and for each write "
        f'1-2 "why it fits you" sentences addressed to the person, in {lang}. '
        'Reply strictly as JSON: {"order": ["slug1", ...], "why": {"slug1": "text", ...}}'
    )
    return _SYSTEM, user


async def rerank_and_explain(
    profile: dict, occupations: list[dict], locale: str
) -> dict | None:
    """Returns {"order": [slug...], "why": {slug: text}, "audit": {...}} or None
    if the LLM is unavailable / returned unusable output."""
    if not occupations:
        return None
    provider = get_provider()
    system, user = build_prompt(profile, occupations, locale)
    req = LLMRequest(
        feature="rerank",
        # haiku: fast (~10s) and $0 on the Max plan; ample for 1-2 sentence
        # "why you" text. sonnet took ~54s and grazed the timeout.
        model="haiku",
        system_prompt=system,
        user_prompt=user,
        locale=locale,
        max_tokens=1400,
        temperature=0.4,
        timeout_s=90,
    )
    try:
        res = await provider.complete_json(req)
    except LLMUnavailable as exc:
        _log.info("ai.rerank.unavailable", error=str(exc))
        return None

    known = {o["slug"] for o in occupations}
    try:
        data = json.loads(res.text)
        order = [s for s in data.get("order", []) if s in known]
        why = {k: str(v) for k, v in (data.get("why") or {}).items() if k in known}
    except Exception as exc:  # noqa: BLE001 — bad LLM output degrades to deterministic
        _log.warning("ai.rerank.bad_output", error=str(exc))
        return None
    if not order:
        return None

    return {
        "order": order,
        "why": why,
        "audit": {
            "backend": res.backend,
            "model": res.model,
            "prompt_hash": hashlib.sha256((system + user).encode()).hexdigest(),
            "tokens": res.input_tokens + res.output_tokens,
            "latency_ms": res.latency_ms,
        },
    }
