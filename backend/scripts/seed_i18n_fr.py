"""Add French (locale='fr') i18n rows to EXISTING catalog occupations (FR-1).

    python -m scripts.seed_i18n_fr [--files seed/i18n_fr_batchA.json,...]

Additive and idempotent — upserts OccupationI18n rows only, NEVER touches
occupations, facts, or other locales (deliberately narrower than
catalog_ingest, which would overwrite facts with LLM drafts). Re-running after
a translation fix self-heals prod.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db import SessionLocal
from app.models import Occupation, OccupationI18n
from sqlalchemy import select

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
DEFAULT_FILES = "seed/i18n_fr_batchA.json,seed/i18n_fr_batchB.json,seed/i18n_fr_batchC.json"
FIELDS = ("title", "summary", "day_in_life", "who_fits")


async def run(paths: list[Path]) -> None:
    data: dict[str, dict] = {}
    for p in paths:
        data.update(json.loads(p.read_text("utf-8")))
    for slug, item in data.items():
        for f in FIELDS:
            if not (item.get(f) or "").strip():
                raise SystemExit(f"empty field {f!r} for slug {slug!r} — refusing to seed")
        if len(item["title"]) > 96:
            raise SystemExit(f"title too long (>96) for {slug!r}: {item['title']!r}")

    async with SessionLocal() as s:
        occ_by_slug = {
            o.slug: o.id for o in (await s.execute(select(Occupation))).scalars().all()
        }
        fr_rows = (
            await s.execute(select(OccupationI18n).where(OccupationI18n.locale == "fr"))
        ).scalars().all()
        fr_by_occ = {r.occupation_id: r for r in fr_rows}

        inserted = updated = skipped = 0
        missing: list[str] = []
        for slug, item in sorted(data.items()):
            oid = occ_by_slug.get(slug)
            if oid is None:
                missing.append(slug)
                continue
            row = fr_by_occ.get(oid)
            if row is None:
                s.add(
                    OccupationI18n(
                        occupation_id=oid,
                        locale="fr",
                        title=item["title"],
                        summary=item["summary"],
                        day_in_life=item["day_in_life"],
                        who_fits=item["who_fits"],
                        content_source="translated",
                    )
                )
                inserted += 1
            elif any(getattr(row, f) != item[f] for f in FIELDS):
                for f in FIELDS:
                    setattr(row, f, item[f])
                updated += 1
            else:
                skipped += 1

        await s.commit()
        print(f"[seed_i18n_fr] +{inserted} inserted, ~{updated} updated, ={skipped} unchanged")
        if missing:
            print(f"[seed_i18n_fr] no occupation for: {', '.join(missing)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", default=DEFAULT_FILES)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    paths = [root / f.strip() for f in args.files.split(",") if f.strip()]
    asyncio.run(run(paths))


if __name__ == "__main__":
    main()
