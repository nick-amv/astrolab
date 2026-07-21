"""Build the FR salary base from INSEE 'Structure des salaires 2022' (public).

Source: INSEE dataset 8541661, table T7_CHP3_PROF (private sector, 1+ employee):
distribution of gross annual pay (DIST_REMU, EUR) by decile D1..D9, broken down
by the 1-digit occupational group (column CITP = ISCO-08 major group). This is a
GROUP-level base (like Spain's INE group figures) — coarse by design; the Adzuna
fetch (fetch_fr_facts_adzuna) upgrades individual professions where enough live
ads exist, and this base fills the rest + gives a ratio sanity-check.

Method per slug:
- map slug -> ISCO major group (SLUG_TO_ISCO); public-sector-only jobs (police,
  firefighter) and professions the group figure clearly misleads (dentist,
  airline-pilot — liberal/very-high or contaminated) are left OUT (no base,
  honest);
- read the group's SEXE=E (both sexes) DIST_REMU deciles;
- p25 = interp between D2 (20th) and D3 (30th); p75 between D7 and D8; median=D5;
- rescale 2022 -> 2024 by the private-sector wage growth (SCALE), round to 100.

Run:  python -m scripts.fetch_fr_facts \
          --src seed/insee_src/T7_CHP3_PROF.csv --out seed/facts_fr.json
Then: python -m scripts.seed_facts --file seed/facts_fr.json   (INSEE first,
      then fetch_fr_facts_adzuna output on top).
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Private-sector nominal wage growth 2022 -> 2024 (INSEE SMPT: +4.2% then ~+3%).
SCALE = 1.073
AS_OF = "2024-01-01"

# Professions where the coarse "professionals" group figure (~36-68k) clearly
# OVERSELLS the real French pay (precarious arts/media or public-sector roles) —
# hidden rather than shown a misleading group estimate. They keep whatever the
# Adzuna upgrade finds; with no Adzuna they show no salary (honest). Anything
# where the group band is a fair proxy (commercial/tech/science) is kept.
HIDE_INACCURATE = {
    "actor", "musician", "librarian", "journalist", "translator", "school-counselor",
}

# slug -> ISCO-08 major group (1 Managers, 2 Professionals, 3 Technicians/assoc,
# 4 Clerical, 5 Service/sales, 8 Plant/machine operators, 9 Elementary). Group 7
# (craft/trades) is absent from the INSEE table, so trades map to 8 (operators),
# the nearest manual band. None = deliberately no base (see module docstring).
SLUG_TO_ISCO: dict[str, int | None] = {
    # managers
    "operations-manager": 1, "sales-manager": 1,
    # professionals — engineering / IT / science / finance / law / health / arts
    "architect": 2, "civil-engineer": 2, "mechanical-engineer": 2,
    "electrical-engineer": 2, "software-developer": 2, "data-scientist": 2,
    "data-engineer": 2, "data-analyst": 2, "machine-learning-engineer": 2,
    "devops-engineer": 2, "database-administrator": 2, "cybersecurity-specialist": 2,
    "network-engineer": 2, "qa-engineer": 2, "game-developer": 2,
    "product-manager": 2, "project-manager": 2, "management-consultant": 2,
    "marketing-manager": 2, "hr-specialist": 2, "financial-analyst": 2,
    "financial-advisor": 2, "economist": 2, "actuary": 2, "statistician": 2,
    "lawyer": 2, "physician": 2, "pharmacist": 2, "veterinarian": 2,
    "psychologist": 2, "biologist": 2, "chemist": 2, "environmental-scientist": 2,
    "urban-planner": 2, "industrial-designer": 2, "interior-designer": 2,
    "journalist": 2, "writer": 2, "translator": 2, "librarian": 2,
    "school-counselor": 2, "teacher": 2, "actor": 2, "musician": 2,
    "art-director": 2, "animator": 2, "ux-ui-designer": 2, "graphic-designer": 2,
    "speech-language-pathologist": 2, "occupational-therapist": 2, "social-worker": 2,
    "physical-therapist": 2,
    # technicians & associate professionals — allied health / support / media
    "it-support-specialist": 3, "systems-administrator": 3, "nurse": 3,
    "radiologic-technologist": 3, "dental-hygienist": 3, "respiratory-therapist": 3,
    "surgical-technologist": 3, "phlebotomist": 3, "medical-assistant": 3,
    "dietitian": 3, "optometrist": 3, "paramedic": 3, "fitness-trainer": 3,
    "insurance-agent": 3, "real-estate-agent": 3, "photographer": 3,
    "sound-engineer": 3, "video-editor": 3, "aircraft-mechanic": 3,
    "accountant": 3, "logistician": 3,
    # service / sales
    "chef": 5,
    # trades (ISCO 7 absent -> nearest band 8, operators)
    "electrician": 8, "plumber": 8, "welder": 8, "carpenter": 8, "machinist": 8,
    "cnc-machinist": 8, "hvac-technician": 8, "automotive-technician": 8,
    "lineworker": 8, "heavy-equipment-operator": 8,
    # deliberately no base (public-sector-only or group figure clearly misleads)
    "police-officer": None, "firefighter": None, "airline-pilot": None,
    "dentist": None,
}


def _deciles(src: Path) -> dict[int, list[float]]:
    """{isco_group: [D1..D9]} from the ensemble-sex gross-annual rows."""
    out: dict[int, list[float]] = {}
    with src.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            if row.get("VAR") != "DIST_REMU" or row.get("SEXE") != "E":
                continue
            code = row.get("CITP", "")
            if not code.isdigit():
                continue
            out[int(code)] = [float(row[f"D{i}"].replace(",", ".")) for i in range(1, 10)]
    return out


def _pctl(dec: list[float], p: float) -> float:
    """Linear interpolation of percentile p (0..100) from deciles D1..D9."""
    # D_k covers the (10*k)th percentile; interpolate between neighbours.
    x = p / 10.0
    lo = max(1, min(9, int(x)))
    frac = x - lo
    d_lo = dec[lo - 1]
    d_hi = dec[min(9, lo + 1) - 1]
    return d_lo + frac * (d_hi - d_lo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=str(ROOT / "seed" / "insee_src" / "T7_CHP3_PROF.csv"))
    ap.add_argument("--out", default=str(ROOT / "seed" / "facts_fr.json"))
    args = ap.parse_args()

    dec = _deciles(Path(args.src))
    if not dec:
        raise SystemExit("no DIST_REMU/SEXE=E rows parsed — check the source file")

    rows = []
    skipped = []
    for slug, grp in SLUG_TO_ISCO.items():
        if grp is None or grp not in dec or slug in HIDE_INACCURATE:
            skipped.append(slug)
            continue
        d = dec[grp]
        lo = int(round(_pctl(d, 25) * SCALE / 100) * 100)
        hi = int(round(_pctl(d, 75) * SCALE / 100) * 100)
        med = int(round(_pctl(d, 50) * SCALE / 100) * 100)
        rows.append({
            "slug": slug, "salary_low": lo, "salary_high": hi,
            "currency": "EUR", "period": "year", "confidence": "estimate",
            "median": med, "isco_group": grp,
        })
    rows.sort(key=lambda r: r["slug"])

    out = {
        "country": "FR",
        "source_key": "insee-ses",
        "source_name": "INSEE Structure des salaires 2022 — distribution par groupe "
                       "socioprofessionnel (brut annuel, secteur privé), rééchelonnée 2024",
        "source_url": "https://www.insee.fr/fr/statistiques/8541661",
        "as_of_date": AS_OF,
        "_doc": "GROUP-level base (ISCO-08 major group), coarse by design; Adzuna "
                "upgrades individual professions where enough live ads exist. "
                f"p25/p75 interpolated from deciles, x{SCALE} to 2024. isco_group is "
                "kept for provenance, not seeded.",
        "facts": rows,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fetch_fr_facts] wrote {len(rows)} group-base facts, skipped {len(skipped)}: {skipped}")
    for r in rows:
        print(f"  {r['slug']:28} g{r['isco_group']}  {r['salary_low']:>7,}-{r['salary_high']:<7,}  med {r['median']:,}")


if __name__ == "__main__":
    main()
