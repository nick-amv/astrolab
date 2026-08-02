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

import json

import structlog

from app.assessment.audit import audit_of
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

_LANG = {"ru": "Russian", "en": "English", "de": "German", "es": "Spanish", "fr": "French"}

_SYSTEM = (
    "You are a warm, honest career-guidance mentor for teenagers and adults. "
    "Given a person's interest profile (RIASEC model), work values, and favourite "
    "school subjects, explain why specific occupations fit THIS person. "
    "Rules: 1-2 short sentences per occupation; concrete and kind; no cliches, no "
    "promises of wealth, no pressure; never invent occupations outside the given "
    "list. "
    # Learned from a model bench on the real prompt: without these two rules the
    # output drifts between formal/informal address inside one response and
    # reuses the same clause ("you can work independently") for half the list.
    "Ground every explanation in something specific to this person — a named "
    "subject, a value, or a statement they reacted to — and say what the daily "
    "work actually involves; a sentence that would fit any of the occupations is "
    "a failed sentence. Never reuse the same reason for two occupations. "
    "Address the person consistently throughout, in the form given below. "
    "Return STRICT JSON only."
)

# Russian and German (and, less strictly, Spanish and French) force a T-V choice
# the model otherwise re-decides per occupation, so one answer ends up mixing
# both. Phrased in English, no locale literals — same reason the rest of the
# prompt is locale-agnostic.
_ADDRESS = {
    "14-16": "informally, the way you would speak to a teenager (in languages with a "
    "T-V distinction, use the familiar form)",
    "17-19": "informally, the way you would speak to a student (in languages with a "
    "T-V distinction, use the familiar form)",
}
_ADDRESS_ADULT = (
    "politely, the way you would speak to an adult you have just met (in languages "
    "with a T-V distinction, use the polite form)"
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


def _interview_summary(interview: list[dict] | None) -> str:
    if not interview:
        return ""
    parts = []
    for it in interview:
        text = it.get("text")
        v = it.get("value", 0)
        stance = "agrees" if v >= 0.75 else ("neutral" if v >= 0.4 else "disagrees")
        if text:
            parts.append(f'"{text}" — {stance}')
    if not parts:
        return ""
    return "\nThe person also reflected on these statements:\n" + "\n".join(parts) + "\n"


def _cv_summary(cv: dict | None) -> str:
    if not cv:
        return ""
    parts = []
    if cv.get("summary"):
        parts.append(f"Current background: {cv['summary']}")
    if cv.get("field"):
        parts.append(f"Field: {cv['field']}")
    if cv.get("skills"):
        parts.append("Transferable skills: " + ", ".join(cv["skills"]))
    if not parts:
        return ""
    return "\n" + ". ".join(parts) + ".\n"


def build_prompt(
    profile: dict,
    occupations: list[dict],
    locale: str,
    interview: list[dict] | None = None,
    cv: dict | None = None,
) -> tuple[str, str]:
    lines = [
        f"- {o['slug']}: {o['title']} (RIASEC "
        + ", ".join(f"{k}{v:.1f}" for k, v in (o.get("riasec") or {}).items())
        + ")"
        for o in occupations
    ]
    lang = _LANG.get(locale, "English")
    cv_hint = (
        "The person is an adult with prior experience; frame each 'why' as a realistic "
        "transition from their background, and hint at what would transfer. "
        if cv
        else ""
    )
    # An adult (CV present) is always addressed formally; otherwise the age band
    # decides. Absent age band → adult, the safer default for a stranger.
    address = _ADDRESS_ADULT if cv else _ADDRESS.get(profile.get("age_band", ""), _ADDRESS_ADULT)
    user = (
        f"{_profile_summary(profile)}\n"
        + _cv_summary(cv)
        + _interview_summary(interview)
        + "\nCandidate occupations (only from this list, do not add any):\n"
        + "\n".join(lines)
        + "\n\nSort them by how well they fit THIS specific person, and for each write "
        f'1-2 "why it fits you" sentences addressed to the person, in {lang}. '
        f"Address them {address}, and keep that form in every sentence. "
        + cv_hint
        + "If the reflections above are present, let them shape the wording. "
        'Reply strictly as JSON: {"order": ["slug1", ...], "why": {"slug1": "text", ...}}'
    )
    return _SYSTEM, user


async def rerank_and_explain(
    profile: dict,
    occupations: list[dict],
    locale: str,
    interview: list[dict] | None = None,
    cv: dict | None = None,
) -> dict | None:
    """Returns {"order": [slug...], "why": {slug: text}, "audit": {...}} or None
    if the LLM is unavailable / returned unusable output."""
    if not occupations:
        return None
    provider = get_provider("rerank")
    system, user = build_prompt(profile, occupations, locale, interview, cv)
    req = LLMRequest(
        feature="rerank",
        # model=None → each backend's own default (max_cli=opus-5 on the
        # subscription, openrouter=its configured model). No backend-specific
        # alias leaks into the feature code.
        model=None,
        system_prompt=system,
        user_prompt=user,
        locale=locale,
        max_tokens=1400,
        temperature=0.4,
        # A live prod run took 66s (vs 27s on the isolated bench — the real
        # prompt is bigger and the subscription CLI is shared with other jobs on
        # this host). 90s left too little headroom before degrading to the paid
        # fallback; nothing waits on this call, so buy the margin.
        timeout_s=150,
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

    return {"order": order, "why": why, "audit": audit_of(res, system, user)}
