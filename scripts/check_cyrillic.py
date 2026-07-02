#!/usr/bin/env python3
"""CI guard: no user-facing string may be hardcoded in source.

DESIGN §9 rule — the only place Cyrillic (or any localized text) belongs is the
Paraglide message catalogs and the DB `*_i18n` tables. Code carries keys, not
strings. This scans source trees for any Cyrillic character and fails if found,
excluding message catalogs, generated output, and docs.

Run from the repo root:  python scripts/check_cyrillic.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCAN_DIRS = [
    "backend/app",
    "backend/scripts",
    "backend/alembic",
    "frontend/src",
]

# Excluded: message catalogs (Cyrillic is expected), generated Paraglide output,
# docs, and anything not source.
EXCLUDE_PARTS = {"paraglide", "node_modules", "__pycache__", ".svelte-kit", "build"}

CYRILLIC = re.compile(r"[Ѐ-ӿ]")
SOURCE_SUFFIXES = {".py", ".ts", ".js", ".svelte", ".html", ".css", ".json", ".mako"}


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDE_PARTS for part in path.parts)


def main() -> int:
    offenders: list[tuple[str, int, str]] = []
    for rel in SCAN_DIRS:
        base = ROOT / rel
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
                continue
            if is_excluded(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if CYRILLIC.search(line):
                    offenders.append((str(path.relative_to(ROOT)), i, line.strip()[:80]))

    if offenders:
        print("Cyrillic found in source (use i18n keys, not literals):")
        for file, line_no, snippet in offenders:
            print(f"  {file}:{line_no}: {snippet}")
        return 1
    print("OK: no hardcoded Cyrillic in source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
