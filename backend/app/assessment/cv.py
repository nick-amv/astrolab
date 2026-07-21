"""CV extraction for the adult flow (Wave 5).

Given pasted resume / experience text, one LLM call (haiku) extracts a short
summary, a list of transferable skills, and the current field. Used to make the
result transition-aware ("with your background in X, moving to Y means…").

Prompt is English with a language directive (locale-agnostic; the model replies
in the user's language). Degradable: returns None if the LLM is unavailable.
"""

from __future__ import annotations

import json

import structlog

from app.llm import LLMRequest, LLMUnavailable, get_provider

_log = structlog.get_logger("astrolab.cv")

_LANG = {"ru": "Russian", "en": "English", "de": "German", "es": "Spanish", "fr": "French"}

_SYSTEM = (
    "You extract structured career context from a person's pasted resume or free "
    "description of their experience. Return STRICT JSON only. Be faithful to the "
    "text; do not invent experience the person did not mention."
)


async def extract_cv(text: str, locale: str) -> dict | None:
    text = (text or "").strip()
    if len(text) < 20:
        return None
    lang = _LANG.get(locale, "English")
    user = (
        "Here is the person's experience (resume or free text):\n\n"
        + text[:6000]
        + "\n\nExtract, in "
        + lang
        + ", strictly as JSON: "
        '{"summary": "one sentence about who they are professionally", '
        '"field": "their current field in 1-3 words", '
        '"skills": ["up to 8 transferable skills"]}'
    )
    req = LLMRequest(
        feature="cv",
        model=None,  # backend default: openrouter=gpt-4o-mini / max_cli=haiku
        system_prompt=_SYSTEM,
        user_prompt=user,
        locale=locale,
        max_tokens=600,
        temperature=0.2,
        timeout_s=90,
    )
    try:
        res = await get_provider().complete_json(req)
    except LLMUnavailable as exc:
        _log.info("cv.unavailable", error=str(exc))
        return None
    try:
        data = json.loads(res.text)
    except Exception as exc:  # noqa: BLE001
        _log.warning("cv.bad_output", error=str(exc))
        return None
    return {
        "summary": str(data.get("summary", ""))[:400],
        "field": str(data.get("field", ""))[:80],
        "skills": [str(s)[:60] for s in (data.get("skills") or [])][:8],
    }
