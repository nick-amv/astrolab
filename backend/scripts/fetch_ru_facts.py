"""Generate seed/facts_ru.json from the Rosstat occupational wage survey.

Real official data (honesty-first): Rosstat's biennial "wage by occupation and
position" survey (OZPP), October 2023, mean monthly wage per OKZ occupational
group. hh.ru's open API is OAuth-gated, so Rosstat is the sourced RU anchor.

Prep (one-off; rosstat.gov.ru is reachable from a Russian IP, not from foreign
hosts, and ships a RAR that needs 7-Zip / unrar):

    curl -L --ssl-no-revoke -o sved.rar \\
      https://rosstat.gov.ru/storage/mediabank/sved_57-t_2023.rar
    7z x sved.rar          # extracts the statistical-bulletin .xlsx

Then:  python -m scripts.fetch_ru_facts --xlsx path/to/bulletin.xlsx

Sheet "9" (composite OKZ groups, all ownership) has, per occupational group,
column 0 = group name and column 2 = mean monthly wage in RUB. Each of our
occupations is mapped (curated) to its OKZ group. Two adjustments, both stated:
  * OCT-2023 -> current: scale by Rosstat's own economy-wide average nominal
    wage growth, 2023 -> 2025 = 100360 / 74854 = x1.341 (rosstat.gov.ru).
  * mean -> range: the survey gives a group MEAN only, so salary_low/high are a
    band (x0.75 / x1.35) around the adjusted mean, not sourced percentiles.
A few occupations whose OKZ group mean clearly misfits the specific job
(pro-athlete-inflated "sport", broad "vessel technicians" for pilots) are left
OUT so their existing per-occupation estimate stays. confidence stays
"estimate": a group mean + growth + band is honestly an estimate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import openpyxl

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
BATCHES = ["occupations_batch1.json", "occupations_batch2.json", "occupations_batch3.json"]
GROWTH = 100360 / 74854  # Rosstat avg nominal wage 2023 -> 2025 (~x1.341)
LOW_MULT, HIGH_MULT = 0.75, 1.35  # band around the adjusted group mean

# occupation slug -> row index within sheet "9" data rows (name+wage). None keeps
# the existing per-occupation estimate (OKZ group mean misfits the job).
SLUG_TO_OKZ_ROW: dict[str, int | None] = {
    "software-developer": 29,
    "data-analyst": 29,
    "data-scientist": 29,
    "qa-engineer": 29,
    "devops-engineer": 29,
    "game-developer": 29,
    "data-engineer": 29,
    "machine-learning-engineer": 29,
    "systems-administrator": 30,
    "network-engineer": 30,
    "database-administrator": 30,
    "cybersecurity-specialist": 30,
    "it-support-specialist": 53,
    "physician": 16,
    "dentist": 16,
    "nurse": 42,
    "medical-assistant": 42,
    "dental-hygienist": 42,
    "pharmacist": 41,
    "radiologic-technologist": 41,
    "veterinarian": 19,
    "physical-therapist": 20,
    "occupational-therapist": 20,
    "optometrist": 20,
    "dietitian": 20,
    "paramedic": 18,
    "respiratory-therapist": 44,
    "surgical-technologist": 44,
    "phlebotomist": 44,
    "psychologist": 33,
    "accountant": 26,
    "financial-analyst": 26,
    "economist": 26,
    "financial-advisor": 26,
    "teacher": 23,
    "speech-language-pathologist": 25,
    "school-counselor": 25,
    "mechanical-engineer": 13,
    "civil-engineer": 13,
    "electrical-engineer": 14,
    "architect": 15,
    "graphic-designer": 15,
    "ux-ui-designer": 15,
    "interior-designer": 15,
    "art-director": 15,
    "industrial-designer": 15,
    "urban-planner": 15,
    "biologist": 12,
    "environmental-scientist": 12,
    "chemist": 10,
    "animator": 35,
    "photographer": 35,
    "video-editor": 35,
    "musician": 35,
    "actor": 35,
    "journalist": 34,
    "writer": 34,
    "translator": 34,
    "chef": 64,
    "marketing-manager": 28,
    "sales-manager": 28,
    "product-manager": 28,
    "project-manager": 27,
    "hr-specialist": 27,
    "management-consultant": 27,
    "logistician": 27,
    "operations-manager": 1,
    "social-worker": 50,
    "lawyer": 31,
    "librarian": 32,
    "actuary": 11,
    "statistician": 11,
    "plumber": 80,
    "hvac-technician": 85,
    "aircraft-mechanic": 85,
    "automotive-technician": 85,
    "carpenter": 91,
    "machinist": 84,
    "cnc-machinist": 84,
    "heavy-equipment-operator": 106,
    "lineworker": 88,
    "electrician": 88,
    "welder": 83,
    "real-estate-agent": 47,
    "insurance-agent": 47,
    "sound-engineer": 54,
    "police-officer": 75,
    "firefighter": 75,
    "airline-pilot": None,  # OKZ "vessel technicians" understates airline pilots
    "fitness-trainer": None,  # OKZ "sport workers" inflated by pro athletes
}


def _round_k(x: float) -> int:
    return int(round(x / 1000.0)) * 1000


def _okz_rows(xlsx: Path) -> list[tuple[str, int]]:
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb["9"]
    rows: list[tuple[str, int]] = []
    for r in ws.iter_rows(values_only=True):
        name, wage = r[0], r[2]
        if (
            isinstance(name, str)
            and name.strip()
            and isinstance(wage, (int, float))
            and wage > 10000
        ):
            rows.append((name.strip(), round(wage)))
    return rows


def _demand_notes() -> dict[str, str | None]:
    dem: dict[str, str | None] = {}
    for name in BATCHES:
        for occ in json.loads((SEED_DIR / name).read_text("utf-8")):
            facts = occ.get("facts") or []
            if facts:
                dem[occ["slug"]] = facts[0].get("demand_note")
    return dem


def run(xlsx: Path) -> None:
    rows = _okz_rows(xlsx)
    dem = _demand_notes()
    facts = []
    for slug, idx in SLUG_TO_OKZ_ROW.items():
        if idx is None:
            continue
        group, mean = rows[idx]
        adj = mean * GROWTH
        facts.append(
            {
                "slug": slug,
                "okz_group": group,
                "salary_low": _round_k(adj * LOW_MULT),
                "salary_high": _round_k(adj * HIGH_MULT),
                "currency": "RUB",
                "period": "month",
                "demand_note": dem.get(slug),
                "confidence": "estimate",
            }
        )
    out = {
        "country": "RU",
        "source_key": "rosstat-ozpp",
        "source_name": "Rosstat occupational wage survey (Oct 2023), scaled to 2025 wage growth",
        "source_url": "https://rosstat.gov.ru/compendium/document/60671",
        "as_of_date": "2025-01-01",
        "facts": facts,
    }
    (SEED_DIR / "facts_ru.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )
    kept = [s for s, i in SLUG_TO_OKZ_ROW.items() if i is None]
    print(f"[fetch_ru_facts] wrote {len(facts)} facts; left as estimate: {kept}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True, help="path to the extracted Rosstat bulletin .xlsx")
    args = ap.parse_args()
    run(Path(args.xlsx))


if __name__ == "__main__":
    main()
