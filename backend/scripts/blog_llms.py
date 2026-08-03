"""Rebuild the "Journal / Articles" section of frontend/static/llms.txt from the
blog manifest — the deterministic post-pass that keeps our AI-agent index in sync
with what is actually published.

llms.txt is what an answer engine reads to decide whether we are worth citing, so
every article must appear there with an evidence line (named source + number).
Rather than hand-maintaining that list (it silently fell 3 articles behind), we
generate it: run this after blog_index.py and the section is always current.

Per article we take, from the EN version (llms.txt is English, and the EN URL is
what we want cited):
  title  <- <meta property="og:title">, else <h1>
  note   <- <meta name="llms-note">, else <meta name="description">

An article can therefore ship a richer, multi-source evidence line by adding
`<meta name="llms-note" content="...">` to its EN file; without one, the meta
description (which our spec already requires to carry a named source and a
number) is used, so a new article is never missing from the index.

Everything outside the section is left untouched, including its intro line.

Run:  python -m scripts.blog_llms
Exit code 1 (with warnings on stdout) if an article could not be indexed — the
autopost validation gate treats that as "do not publish".
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

from scripts.blog_slugs import slug_for, url_for

ROOT = Path(__file__).resolve().parents[2]
BLOG = ROOT / "frontend" / "static" / "blog"
LLMS = ROOT / "frontend" / "static" / "llms.txt"
HOST = "https://astrolab.nikam.dev"
SECTION = "## Journal / Articles"

_OG_TITLE = re.compile(r'<meta\s+property="og:title"\s+content="(.*?)"\s*/?>', re.S)
_H1 = re.compile(r"<h1>(.*?)</h1>", re.S)
_NOTE = re.compile(r'<meta\s+name="llms-note"\s+content="(.*?)"\s*/?>', re.S)
_DESC = re.compile(r'<meta\s+name="description"\s+content="(.*?)"\s*/?>', re.S)


def _field(page: str, *patterns: re.Pattern[str]) -> str:
    """First matching pattern, tags stripped and entities decoded."""
    for rx in patterns:
        m = rx.search(page)
        if m:
            text = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                return text
    return ""


def _lines() -> tuple[list[str], list[str]]:
    manifest = json.loads((BLOG / "index.json").read_text("utf-8"))
    lines, problems = [], []
    for art in manifest:
        slug = art["slug"]  # article id; the EN file has its own localized slug
        page = BLOG / "en" / f"{slug_for(slug, 'en')}.html"
        if not page.exists():
            problems.append(f"{slug}: no EN version — not indexed in llms.txt")
            continue
        source = page.read_text("utf-8")
        title = _field(source, _OG_TITLE, _H1)
        note = _field(source, _NOTE, _DESC)
        if not title or not note:
            problems.append(f"{slug}: missing EN title/note (og:title, llms-note or description)")
            continue
        lines.append(f"- {title} — {HOST}{url_for(slug, 'en')} — {note}")
    return lines, problems


def main() -> int:
    lines, problems = _lines()
    if not lines:
        print("[blog_llms] no articles resolved — llms.txt left untouched")
        return 1

    text = LLMS.read_text("utf-8")
    if SECTION not in text:
        print(f"[blog_llms] '{SECTION}' section not found in llms.txt")
        return 1

    head, _, rest = text.partition(SECTION)
    # the section runs until the next "## " heading (or EOF)
    tail_match = re.search(r"^## ", rest, re.M)
    body, tail = (rest[: tail_match.start()], rest[tail_match.start():]) if tail_match else (rest, "")
    # keep whatever intro prose sits between the heading and the first bullet
    intro = [ln for ln in body.splitlines() if ln.strip() and not ln.lstrip().startswith("- ")]

    section = "\n".join([SECTION, *intro, *lines])
    new = f"{head}{section}\n\n{tail}" if tail else f"{head}{section}\n"

    changed = new != text
    if changed:
        LLMS.write_text(new, encoding="utf-8")
    for p in problems:
        print(f"[blog_llms] WARN {p}")
    verb = "updated" if changed else "already current"
    print(f"[blog_llms] llms.txt {verb}: {len(lines)} articles indexed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
