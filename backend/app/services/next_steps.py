"""Curated 'what next' action steps per field of study (N4).

No LLM: static, localized templates so a result turns from 'here is who you are'
into 'here is what to do this week'. Links are SEARCH urls (never a specific
video or course) so they never rot. Content lives in seed/next_steps.json.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

_SEED = Path(__file__).resolve().parents[2] / "seed" / "next_steps.json"

_TEEN_BANDS = {"14-16", "17-19"}


def audience_for(age_band: str | None) -> str:
    """Teen flow (parents involved) vs everyone else. Drives which step set to show."""
    return "teen" if age_band in _TEEN_BANDS else "adult"


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(_SEED.read_text(encoding="utf-8"))


def _url(link: dict | None, occupation: str, locale: str) -> str | None:
    if not link:
        return None
    q = quote_plus(link["q"].replace("{occupation}", occupation))
    if link["t"] == "youtube":
        return f"https://www.youtube.com/results?search_query={q}"
    if link["t"] == "course":
        # Free intro courses: Stepik for RU, Coursera elsewhere (search pages).
        return (
            f"https://stepik.org/catalog/search?query={q}"
            if locale == "ru"
            else f"https://www.coursera.org/search?query={q}"
        )
    return None


def resolve_steps(
    field_tag: str | None, audience: str, locale: str, occupation: str
) -> list[dict]:
    """3 generic steps for the audience + 1 field-specific weekend micro-trial.

    Returns [{idx, text, url|None}]; idx is stable (used as plan_items.step_idx).
    """
    data = _data()
    loc = locale if locale in ("ru", "en", "es") else "ru"
    aud = audience if audience in ("teen", "adult") else "adult"
    common = data["common"][aud].get(loc) or data["common"][aud]["ru"]
    field = (data["by_field"].get(field_tag or "") or {}).get(loc)
    raw = list(common) + ([field] if field else [])
    return [
        {
            "idx": i,
            "text": s["text"].replace("{occupation}", occupation),
            "url": _url(s.get("link"), occupation, loc),
        }
        for i, s in enumerate(raw)
    ]
