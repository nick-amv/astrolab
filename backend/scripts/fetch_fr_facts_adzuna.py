"""Fetch FR salary facts from live job ads via the Adzuna API (France).

Per-profession upgrade over the INSEE group facts (fetch_fr_facts): where enough
salaried ads exist, the profession gets its own p25-p75 from the open hiring
market; thin professions keep the INSEE group figure (seed order: INSEE first,
this file after).

Method:
- per slug, 1-2 title_only queries (seed/adzuna_queries_fr.json; French title
  + an English variant for roles hired with English titles), salary_min=1,
  up to --pages pages of 50, merged and deduped by ad id;
- one value per ad: mid of salary_min/max (Adzuna normalizes to EUR/year);
- garbage guards: ads whose title names another country are dropped (boards
  carry 'Infirmier en Suisse' style foreign offers), plausibility window
  12k-160k EUR/yr (mis-parsed monthly rates show up as 300k+);
- aggregate p25/median/p75; slugs with n < --min-n are SKIPPED (keep INSEE).

Auth: ADZUNA_APP_ID / ADZUNA_APP_KEY from env (/etc/astrolab/env on prod).
Trial tier limits ~25 req/min, ~250/day - the script paces itself. Run manually:

    python -m scripts.fetch_fr_facts_adzuna --compare seed/facts_fr.json \
        --out seed/facts_fr_adzuna.json [--slugs a,b] [--pages 3] [--min-n 18]

Then: python -m scripts.seed_facts --file seed/facts_fr_adzuna.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from statistics import median, quantiles

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.adzuna.com/v1/api/jobs/fr/search/{page}"
UA = "Astrolab/1.0 (diamexx@mail.ru)"
PAUSE = 2.6  # seconds between calls (trial: 25/min)

SAL_MIN, SAL_MAX = 12_000, 160_000  # plausibility window, EUR/year
# ads recruiting FOR another country, posted on French boards
FOREIGN = re.compile(
    r"\b(suisse|luxembourg|belgique|belge|allemagne|canada|qu[eé]bec|espagne|"
    r"royaume[- ]uni|angleterre|irlande|pays[- ]bas|norv[eè]ge|[eé]mirats|qatar|"
    r"arabie|maroc|alg[eé]rie|tunisie|[eé]tranger|expatriation|expat)\b",
    re.IGNORECASE,
)


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def ads_for(
    query: str, app_id: str, app_key: str, pages: int, exclude: re.Pattern | None
) -> dict[str, float]:
    """{ad_id: salary_mid} for salaried, France-located, plausible ads."""
    out: dict[str, float] = {}
    for page in range(1, pages + 1):
        qs = urllib.parse.urlencode(
            {
                "app_id": app_id,
                "app_key": app_key,
                "title_only": query,
                "salary_min": "1",
                "results_per_page": "50",
            }
        )
        try:
            data = _get(API.format(page=page) + "?" + qs)
        except Exception as e:  # noqa: BLE001 - one bad page must not kill the run
            print(f"  WARN {query!r} p{page}: {e}", file=sys.stderr)
            break
        results = data.get("results", [])
        for r in results:
            title = r.get("title") or ""
            if FOREIGN.search(title):
                continue
            # per-slug pollution guard (e.g. 'architecte' must not match
            # software architects, 'animateur' not youth-camp leaders)
            if exclude and exclude.search(title):
                continue
            lo, hi = r.get("salary_min"), r.get("salary_max")
            val = (lo + hi) / 2 if lo and hi else (lo or hi)
            if not val or not SAL_MIN <= val <= SAL_MAX:
                continue
            out[str(r.get("id"))] = float(val)
        time.sleep(PAUSE)
        if len(results) < 50:
            break
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queries", default=str(ROOT / "seed" / "adzuna_queries_fr.json"))
    ap.add_argument("--compare", default=str(ROOT / "seed" / "facts_fr.json"))
    ap.add_argument("--out", default=str(ROOT / "seed" / "facts_fr_adzuna.json"))
    ap.add_argument("--slugs", default="", help="comma-separated subset")
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--min-n", type=int, default=18)
    args = ap.parse_args()

    app_id = os.environ.get("ADZUNA_APP_ID", "")
    app_key = os.environ.get("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        sys.exit("ADZUNA_APP_ID / ADZUNA_APP_KEY not set (source /etc/astrolab/env)")

    queries = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    queries.pop("_doc", None)
    subset = {s for s in args.slugs.split(",") if s}
    baseline: dict[str, dict] = {}
    cmp_path = Path(args.compare)
    if cmp_path.exists():
        for row in json.loads(cmp_path.read_text(encoding="utf-8")).get("facts", []):
            baseline[row["slug"]] = row

    today = dt.date.today().isoformat()
    rows, skipped = [], []
    print(f"{'slug':34} {'n':>5}  {'adzuna p25-p75 EUR/yr':>22}  {'INSEE low-high':>18}  ratio")
    for slug, cfg in queries.items():
        if subset and slug not in subset:
            continue
        excl = re.compile(cfg["exclude"], re.IGNORECASE) if cfg.get("exclude") else None
        ads: dict[str, float] = {}
        for q in cfg["queries"]:
            ads.update(ads_for(q, app_id, app_key, args.pages, excl))
        vals = list(ads.values())
        n = len(vals)
        if n < args.min_n:
            skipped.append((slug, n))
            print(f"{slug:34} {n:>5}  {'-- skipped (thin) --':>22}")
            continue
        q4 = quantiles(vals, n=4)
        lo = int(round(q4[0] / 100) * 100)
        hi = int(round(q4[2] / 100) * 100)
        base = baseline.get(slug) or {}
        b_lo, b_hi = base.get("salary_low"), base.get("salary_high")
        ratio = ""
        if b_lo and b_hi:
            ratio = f"{((lo + hi) / 2) / ((b_lo + b_hi) / 2):.2f}"
        print(f"{slug:34} {n:>5}  {lo:>9,}-{hi:<11,}  {str(b_lo):>8}-{str(b_hi):<9} {ratio}")
        rows.append(
            {
                "slug": slug,
                "salary_low": lo,
                "salary_high": hi,
                "currency": "EUR",
                "period": "year",
                "confidence": "estimate",
                "n": n,
                "median": int(median(vals)),
            }
        )

    out = {
        "country": "FR",
        "source_key": "adzuna-jobs",
        "source_name": "Adzuna live job-ad salary analysis (p25-p75, gross annual, France)",
        "source_url": "https://www.adzuna.fr/",
        "as_of_date": today,
        "facts": rows,
    }
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nwritten {args.out}: {len(rows)} facts, skipped {len(skipped)} thin: "
          f"{[s for s, _ in skipped][:14]}")


if __name__ == "__main__":
    main()
