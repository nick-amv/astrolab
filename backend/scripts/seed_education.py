"""Seed education paths for one country from a seed JSON (idempotent).

    python -m scripts.seed_education [--file seed/education_us.json]

Populates edu_domains (fields of study, OKSO/CIP codes), edu_requirements
(typical exam combos / what-to-take), occupation_edu (occupation -> domain), and
milestones (admission deadlines). The country comes from the file; re-running
wipes only THAT country's rows and re-inserts (so seeding US never touches RU).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db import SessionLocal
from app.models import EduDomain, EduRequirement, Milestone, Occupation, OccupationEdu
from sqlalchemy import delete, select

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
DEFAULT_SEED = SEED_DIR / "education_ru.json"


async def run(seed_path: Path) -> None:
    data = json.loads(seed_path.read_text("utf-8"))
    country = data["country"]

    # Validate BEFORE the wipe: title_key is varchar(96). Catching an overlong
    # title here (rather than mid-insert) avoids emptying a country's education
    # and then failing, which is what a 97-char RU title once did.
    too_long = [d["code"] for d in data["domains"] if len(d["title"]) > 96]
    if too_long:
        raise SystemExit(f"[seed_education] title >96 chars for domains: {too_long}")

    async with SessionLocal() as s:
        # wipe this country (edu_domains cascade to requirements + occupation_edu)
        await s.execute(delete(EduDomain).where(EduDomain.country == country))
        await s.execute(delete(Milestone).where(Milestone.country == country))
        await s.commit()

        occ_by_slug = {
            o.slug: o.id for o in (await s.execute(select(Occupation))).scalars().all()
        }

        n_dom = n_map = 0
        for d in data["domains"]:
            dom = EduDomain(country=country, code=d["code"], title_key=d["title"])
            s.add(dom)
            await s.flush()
            s.add(
                EduRequirement(
                    domain_id=dom.id,
                    data={
                        "level": d.get("level"),
                        "ege": d.get("ege", []),
                        "as_of": data.get("as_of"),
                        "note": data.get("note"),
                    },
                )
            )
            for slug in d.get("occupations", []):
                oid = occ_by_slug.get(slug)
                if oid is not None:
                    s.add(OccupationEdu(occupation_id=oid, domain_id=dom.id, weight=1.0))
                    n_map += 1
            n_dom += 1

        n_ms = 0
        for ms in data.get("milestones", []):
            s.add(
                Milestone(
                    country=country,
                    education_stage=ms["stage"],
                    date_rule=ms["date_rule"],
                    title_key=ms["title"],
                )
            )
            n_ms += 1

        await s.commit()
        print(f"[seed_education] {country}: {n_dom} domains, {n_map} maps, {n_ms} milestones")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT_SEED))
    args = ap.parse_args()
    asyncio.run(run(Path(args.file)))


if __name__ == "__main__":
    main()
