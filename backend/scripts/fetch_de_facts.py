"""Build the DE salary base from the Bundesagentur Entgeltatlas (public).

Source: Bundesagentur fuer Arbeit, Entgeltstatistik — median gross MONTHLY
full-time pay by Anforderungsniveau (skill/requirement level), 2023:
    Helfer 2863, Fachkraft 3720, Spezialist 5005, Experte 6292 (EUR/month).
Scaled to 2024 by the overall median growth (3796 -> 4013 EUR = x1.057), then
annualised x12. This is a GROUP-level base (by requirement level, like Spain's
INE group figures / France's INSEE ISCO groups) — coarse by design; the Adzuna
fetch (fetch_de_facts_adzuna) upgrades individual professions where enough live
ads exist, and this base fills the rest + gives a ratio sanity-check.

Honesty:
- the level MEDIAN is real (cited above); the p25/p75 band is an explicit
  ESTIMATE around that median (confidence='estimate'), disclosed on the method
  page. German figures are censored at the Beitragsbemessungsgrenze
  (~7550 EUR/month = 90600/yr), so the upper band is capped there.
- professions where the level figure clearly OVERSELLS the typical German pay
  (precarious arts) are left out (HIDE) — they keep whatever Adzuna finds, else
  show no salary (honest), mirroring the FR base.

Run:  python -m scripts.fetch_de_facts --out seed/facts_de.json
Then: python -m scripts.seed_facts --file seed/facts_de.json   (base first, then
      the fetch_de_facts_adzuna output on top).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# median gross MONTHLY full-time pay by Anforderungsniveau, Entgeltatlas 2023.
NIVEAU_MEDIAN_2023 = {"helfer": 2863, "fachkraft": 3720, "spezialist": 5005, "experte": 6292}
SCALE_23_24 = 4013 / 3796  # overall median growth 2023 -> 2024 (~1.057)
BBG_YEAR = 90_600  # Beitragsbemessungsgrenze ~7550 EUR/mo x12 — data censored above
LO_MULT, HI_MULT = 0.80, 1.30  # disclosed estimated p25/p75 band around the median
AS_OF = "2024-01-01"

# slug -> Anforderungsniveau. Experte = academic/complex senior (Master/Staats-
# examen); Spezialist = Bachelor/Meister/Techniker specialist; Fachkraft =
# completed Ausbildung; Helfer = no/short qualification. None = deliberately no
# base (level figure misleads for precarious arts). Public-sector Polizei/
# Feuerwehr are included (unlike private-only surveys they exist in this stat).
SLUG_TO_NIVEAU: dict[str, str | None] = {
    # experte — top academic / regulated / senior
    "physician": "experte", "dentist": "experte", "pharmacist": "experte",
    "veterinarian": "experte", "lawyer": "experte", "actuary": "experte",
    "management-consultant": "experte", "data-scientist": "experte",
    "machine-learning-engineer": "experte", "airline-pilot": "experte",
    # spezialist — Bachelor/Meister/Techniker specialist
    "architect": "spezialist", "civil-engineer": "spezialist",
    "mechanical-engineer": "spezialist", "electrical-engineer": "spezialist",
    "software-developer": "spezialist", "data-engineer": "spezialist",
    "data-analyst": "spezialist", "devops-engineer": "spezialist",
    "database-administrator": "spezialist", "cybersecurity-specialist": "spezialist",
    "network-engineer": "spezialist", "qa-engineer": "spezialist",
    "product-manager": "spezialist", "project-manager": "spezialist",
    "economist": "spezialist", "financial-analyst": "spezialist",
    "financial-advisor": "spezialist", "marketing-manager": "spezialist",
    "sales-manager": "spezialist", "operations-manager": "spezialist",
    "hr-specialist": "spezialist", "psychologist": "spezialist",
    "biologist": "spezialist", "chemist": "spezialist",
    "environmental-scientist": "spezialist", "urban-planner": "spezialist",
    "statistician": "spezialist", "industrial-designer": "spezialist",
    "interior-designer": "spezialist", "game-developer": "spezialist",
    "ux-ui-designer": "spezialist", "art-director": "spezialist",
    "animator": "spezialist",
    "teacher": "spezialist", "school-counselor": "spezialist",
    "speech-language-pathologist": "spezialist", "occupational-therapist": "spezialist",
    "physical-therapist": "spezialist", "journalist": "spezialist",
    "translator": "spezialist", "librarian": "spezialist", "social-worker": "spezialist",
    # fachkraft — completed Ausbildung
    "nurse": "fachkraft", "medical-assistant": "fachkraft",
    "radiologic-technologist": "fachkraft", "dental-hygienist": "fachkraft",
    "respiratory-therapist": "fachkraft", "surgical-technologist": "fachkraft",
    "phlebotomist": "fachkraft", "dietitian": "fachkraft", "optometrist": "fachkraft",
    "paramedic": "fachkraft", "fitness-trainer": "fachkraft", "chef": "fachkraft",
    "electrician": "fachkraft", "plumber": "fachkraft", "welder": "fachkraft",
    "carpenter": "fachkraft", "machinist": "fachkraft", "cnc-machinist": "fachkraft",
    "hvac-technician": "fachkraft", "automotive-technician": "fachkraft",
    "lineworker": "fachkraft", "heavy-equipment-operator": "fachkraft",
    "aircraft-mechanic": "fachkraft", "it-support-specialist": "fachkraft",
    "systems-administrator": "fachkraft", "insurance-agent": "fachkraft",
    "real-estate-agent": "fachkraft", "accountant": "fachkraft",
    "logistician": "fachkraft", "graphic-designer": "fachkraft",
    "photographer": "fachkraft", "sound-engineer": "fachkraft",
    "video-editor": "fachkraft", "police-officer": "fachkraft",
    "firefighter": "fachkraft", "writer": "fachkraft",
    # deliberately no base — precarious arts the level median oversells
    "actor": None, "musician": None,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "seed" / "facts_de.json"))
    args = ap.parse_args()

    rows, skipped = [], []
    for slug, niveau in SLUG_TO_NIVEAU.items():
        if niveau is None:
            skipped.append(slug)
            continue
        med_year = NIVEAU_MEDIAN_2023[niveau] * SCALE_23_24 * 12
        med = int(round(med_year / 100) * 100)
        lo = int(round(med_year * LO_MULT / 100) * 100)
        hi = min(BBG_YEAR, int(round(med_year * HI_MULT / 100) * 100))
        rows.append({
            "slug": slug, "salary_low": lo, "salary_high": hi,
            "currency": "EUR", "period": "year", "confidence": "estimate",
            "median": med, "niveau": niveau,
        })
    rows.sort(key=lambda r: r["slug"])

    out = {
        "country": "DE",
        "source_key": "entgeltatlas",
        "source_name": "Bundesagentur fuer Arbeit — Entgeltatlas: Medianentgelt nach "
                       "Anforderungsniveau (brutto, Vollzeit), 2023 auf 2024 skaliert; "
                       "Bandbreite als Schaetzung um den Median",
        "source_url": "https://web.arbeitsagentur.de/entgeltatlas",
        "as_of_date": AS_OF,
        "_doc": "GROUP-level base by Anforderungsniveau (Helfer/Fachkraft/Spezialist/"
                "Experte), coarse by design; Adzuna upgrades individual professions. "
                "Level MEDIAN is real; p25/p75 band is an estimate (x0.80/x1.30), "
                f"capped at the Beitragsbemessungsgrenze ({BBG_YEAR}/yr). niveau kept "
                "for provenance, not seeded.",
        "facts": rows,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fetch_de_facts] wrote {len(rows)} group-base facts, skipped {len(skipped)}: {skipped}")
    for r in rows:
        print(f"  {r['slug']:28} {r['niveau']:10} {r['salary_low']:>7,}-{r['salary_high']:<7,}  med {r['median']:,}")


if __name__ == "__main__":
    main()
