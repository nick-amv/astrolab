"""The article slug registry — one source of truth for Journal URLs.

Each article has an id (the Russian slug) and one slug per locale, so a French
reader gets /blog/fr/erreurs-choix-metier.html rather than a transliterated
Russian one. Everything that emits a Journal URL reads this file: blog_chrome
(canonical, hreflang, language switcher), blog_index (the manifest the index page
and the sitemap read), and the SvelteKit hook that 301s the old URLs.

Keeping it in `frontend/static/blog/` means it ships with the site, so the
frontend hook and the Python post-passes cannot drift apart.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[2] / "frontend" / "static" / "blog" / "slugs.json"
LOCALES = ("ru", "en", "es", "fr", "de")


@lru_cache(maxsize=1)
def registry() -> dict[str, dict[str, str]]:
    raw = json.loads(REGISTRY.read_text("utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def slug_for(article_id: str, loc: str) -> str:
    """Localized slug, falling back to the article id (its Russian slug).

    The fallback keeps a half-registered article reachable instead of building
    URLs to files that do not exist."""
    return registry().get(article_id, {}).get(loc, article_id)


def url_for(article_id: str, loc: str) -> str:
    slug = slug_for(article_id, loc)
    return f"/blog/{slug}.html" if loc == "ru" else f"/blog/{loc}/{slug}.html"


def article_id_of(slug: str, loc: str) -> str | None:
    """Reverse lookup: which article does this locale's slug belong to?"""
    for article_id, slugs in registry().items():
        if slugs.get(loc) == slug:
            return article_id
    return registry().get(slug) and slug  # an id used directly (ru, or pre-rename)
