"""Compute ES salary facts from INE EES 2022 microdata (Spain, ES-3).

Source: Encuesta Cuatrienal de Estructura Salarial 2022 public microdata,
https://www.ine.es/ftp/microdatos/salarial/datos_2022.zip (CSV/EES_2022.tab).
The anonymized file carries occupation as 17 aggregated CNO-11 groups
(letters A0..Q0), so — like the Rosstat pipeline — facts are honest GROUP
figures, labeled as such in the UI.

Method (INE's own published recipe, from the bundled methodology doc):
    DIASRELABA = DRELABAM*30.42 + DRELABAD   (capped at 365)
    DIASANO    = DIASRELABA - DSIESPA2 - DSIESPA4
    SALANUAL   = (365/DIASANO) * (RETRINOIN + RETRIIN + VESPNOIN + VESPIN)
Full-time employees only (TIPOJOR=1); weighted by FACTOTAL. Per group we take
weighted p25/p50/p75 of gross ANNUAL euros, then scale 2022 -> latest EAES
year by the national mean-wage ratio (sourced, not guessed):
EAES 'Todas las ocupaciones' national mean 2022=26948.87, 2024=29540.26.

Run (data lives wherever you unzipped the INE file):
    python -m scripts.fetch_es_facts --file /tmp/ees2022/CSV/EES_2022.tab \
        --out seed/facts_es.json
Then: python -m scripts.seed_facts --file seed/facts_es.json
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GROWTH_2022_TO_LATEST = 29540.26 / 26948.87  # EAES national mean, 2022 -> 2024
AS_OF = "2025-01-01"  # the scaled level ~ start of 2025

# slug -> EES CNO-11 aggregated group (letter code in the public microdata).
# A0 managers | B0 health+education professionals | C0 other professionals |
# D0 technicians/associate | E0 clerical (no public contact) | G0 hospitality/
# sales | H0 care workers | I0 protection | K0 construction trades | L0
# manufacturing trades | N0 mobile-machinery operators
SLUG_TO_GROUP: dict[str, str | None] = {
    "operations-manager": "A0",
    "sales-manager": "A0",
    "physician": "B0",
    "nurse": "B0",
    "dentist": "B0",
    "pharmacist": "B0",
    "veterinarian": "B0",
    "physical-therapist": "B0",
    "psychologist": "B0",
    "teacher": "B0",
    "school-counselor": "B0",
    "optometrist": "B0",
    "dietitian": "B0",
    "speech-language-pathologist": "B0",
    "occupational-therapist": "B0",
    "software-developer": "C0",
    "data-analyst": "C0",
    "data-scientist": "C0",
    "data-engineer": "C0",
    "machine-learning-engineer": "C0",
    "game-developer": "C0",
    "qa-engineer": "C0",
    "devops-engineer": "C0",
    "lawyer": "C0",
    "economist": "C0",
    "financial-analyst": "C0",
    "financial-advisor": "C0",
    "actuary": "C0",
    "statistician": "C0",
    "architect": "C0",
    "urban-planner": "C0",
    "civil-engineer": "C0",
    "electrical-engineer": "C0",
    "mechanical-engineer": "C0",
    "environmental-scientist": "C0",
    "biologist": "C0",
    "chemist": "C0",
    "journalist": "C0",
    "writer": "C0",
    "translator": "C0",
    "librarian": "C0",
    "marketing-manager": "C0",
    "product-manager": "C0",
    "project-manager": "C0",
    "hr-specialist": "C0",
    "management-consultant": "C0",
    "ux-ui-designer": "C0",
    "graphic-designer": "C0",
    "industrial-designer": "C0",
    "interior-designer": "C0",
    "art-director": "C0",
    "animator": "C0",
    "musician": "C0",
    "actor": "C0",
    "social-worker": "C0",
    "systems-administrator": "D0",
    "network-engineer": "D0",
    "database-administrator": "D0",
    "cybersecurity-specialist": "D0",
    "it-support-specialist": "D0",
    "paramedic": "D0",
    "radiologic-technologist": "D0",
    "dental-hygienist": "D0",
    "surgical-technologist": "D0",
    "respiratory-therapist": "D0",
    "photographer": "D0",
    "video-editor": "D0",
    "sound-engineer": "D0",
    "fitness-trainer": "D0",
    "insurance-agent": "D0",
    "real-estate-agent": "D0",
    "logistician": "D0",
    "accountant": "E0",
    "chef": "G0",
    "medical-assistant": "H0",
    "phlebotomist": "H0",
    "police-officer": "I0",
    "firefighter": "I0",
    "electrician": "K0",
    "plumber": "K0",
    "hvac-technician": "K0",
    "carpenter": "K0",
    "lineworker": "K0",
    "welder": "L0",
    "machinist": "L0",
    "cnc-machinist": "L0",
    "automotive-technician": "L0",
    "aircraft-mechanic": "L0",
    "heavy-equipment-operator": "N0",
    # group-level figure would badly mislead for pilots (they sit inside D0):
    "airline-pilot": None,
}


def wpct(pairs: list[tuple[float, float]], q: float) -> float:
    """Weighted percentile: pairs = (value, weight), q in (0,1)."""
    pairs.sort(key=lambda t: t[0])
    total = sum(w for _, w in pairs)
    target = q * total
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= target:
            return v
    return pairs[-1][0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True, help="path to CSV/EES_2022.tab")
    ap.add_argument("--out", default=str(ROOT / "seed" / "facts_es.json"))
    args = ap.parse_args()

    groups: dict[str, list[tuple[float, float]]] = {}
    with open(args.file, encoding="latin1", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["TIPOJOR"].strip().strip('"') != "1":  # full-time only
                continue
            try:
                dias_rel = min(
                    float(row["DRELABAM"]) * 30.42 + float(row["DRELABAD"]), 365.0
                )
                dias = dias_rel - float(row["DSIESPA2"]) - float(row["DSIESPA4"])
                if dias <= 0:
                    continue
                sal = (365.0 / dias) * (
                    float(row["RETRINOIN"])
                    + float(row["RETRIIN"])
                    + float(row["VESPNOIN"])
                    + float(row["VESPIN"])
                )
                w = float(row["FACTOTAL"])
            except (ValueError, KeyError):
                continue
            if not 5000 <= sal <= 400000 or w <= 0:
                continue
            g = row["CNO1"].strip().strip('"')
            groups.setdefault(g, []).append((sal, w))

    stats: dict[str, tuple[int, int, int, int]] = {}
    print(f"{'group':6} {'n':>7}  {'p25':>8} {'p50':>8} {'p75':>8}  (2022 EUR/yr, FT)")
    for g in sorted(groups):
        vals = groups[g]
        p25, p50, p75 = (wpct(vals, q) for q in (0.25, 0.50, 0.75))
        stats[g] = (len(vals), int(p25), int(p50), int(p75))
        print(f"{g:6} {len(vals):>7}  {int(p25):>8} {int(p50):>8} {int(p75):>8}")

    facts = []
    for slug, g in sorted(SLUG_TO_GROUP.items()):
        if g is None or g not in stats:
            continue
        _, p25, _, p75 = stats[g]
        lo = int(round(p25 * GROWTH_2022_TO_LATEST / 100) * 100)
        hi = int(round(p75 * GROWTH_2022_TO_LATEST / 100) * 100)
        facts.append(
            {
                "slug": slug,
                "cno_group": g,
                "salary_low": lo,
                "salary_high": hi,
                "currency": "EUR",
                "period": "year",
                "confidence": "estimate",
            }
        )

    out = {
        "country": "ES",
        "source_key": "ine-ees",
        "source_name": (
            "INE Encuesta de Estructura Salarial 2022 microdata "
            "(weighted p25-p75 by occupation group, full-time, gross annual), "
            "scaled to the latest EAES national wage level"
        ),
        "source_url": "https://www.ine.es/ftp/microdatos/salarial/datos_2022.zip",
        "as_of_date": AS_OF,
        "facts": facts,
    }
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nwritten {args.out}: {len(facts)} facts "
          f"(growth x{GROWTH_2022_TO_LATEST:.4f}, as_of {AS_OF})")


if __name__ == "__main__":
    main()
