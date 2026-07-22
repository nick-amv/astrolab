"""Rebuild the Journal manifest (frontend/static/blog/index.json) from the
article HTML files — the deterministic post-pass for the Astrolab blog.

For each article it extracts, per locale, the <h1> (title) and .dek (dek) from
the self-contained HTML, and writes the multilingual manifest the /blog/ index
page and the sitemap read. Articles are declared in ARTICLES (slug, category,
read_min, date); the newest goes first.

Locales: ru is the flat master (/blog/<slug>.html); en/es/fr/de live under
/blog/<locale>/<slug>.html.

Run:  python -m scripts.blog_index
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BLOG = Path(__file__).resolve().parents[2] / "frontend" / "static" / "blog"
LOCALES = ("ru", "en", "es", "fr", "de")

# newest first. category = canonical RU label (one of the 6 from CONTENT-AGENT).
ARTICLES = [
    {"slug": "chto-takoe-riasec", "category": "Метод и самоопределение", "read_min": 7, "date": "2026-07-22"},
    {"slug": "professii-s-vysokoy-zarplatoy", "category": "Профессии", "read_min": 6, "date": "2026-07-22"},
    {"slug": "kak-vybrat-professiyu", "category": "Выбор профессии", "read_min": 7, "date": "2026-07-22"},
]

_H1 = re.compile(r"<h1>(.*?)</h1>", re.S)
_DEK = re.compile(r'<p class="dek">(.*?)</p>', re.S)


def _text(html: str, rx: re.Pattern) -> str:
    m = rx.search(html)
    if not m:
        return ""
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def _path(loc: str, slug: str) -> Path:
    return BLOG / f"{slug}.html" if loc == "ru" else BLOG / loc / f"{slug}.html"


def _url(loc: str, slug: str) -> str:
    return f"/blog/{slug}.html" if loc == "ru" else f"/blog/{loc}/{slug}.html"


def main() -> None:
    out = []
    problems = []
    for art in ARTICLES:
        slug = art["slug"]
        i18n = {}
        for loc in LOCALES:
            p = _path(loc, slug)
            if not p.exists():
                problems.append(f"{slug}: missing {loc}")
                continue
            html = p.read_text("utf-8")
            title, dek = _text(html, _H1), _text(html, _DEK)
            if not title or not dek:
                problems.append(f"{slug}/{loc}: empty title/dek")
            i18n[loc] = {"title": title, "dek": dek, "url": _url(loc, slug)}
        out.append({
            "slug": slug, "category": art["category"],
            "read_min": art["read_min"], "date": art["date"], "i18n": i18n,
        })

    (BLOG / "index.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[blog_index] wrote index.json: {len(out)} articles, {len(LOCALES)} locales each")
    if problems:
        print("[blog_index] PROBLEMS:", problems)


if __name__ == "__main__":
    main()
