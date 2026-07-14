"""Fetch RU salary facts from live hh.ru vacancies (N6.4).

Methodology (mirrors the honesty rules of fetch_us_facts / fetch_ru_facts):
- per occupation slug, run a name-scoped vacancy search (seed/hh_queries.json,
  text tuned per slug) with only_with_salary=true across all of Russia
  (area=113), up to --pages pages of 100;
- each vacancy contributes one value: the from/to midpoint (or the single
  bound), RUR only; net offers (gross=false) are normalized to gross /0.87 so
  the numbers stay comparable with Rosstat-based facts;
- aggregate p25 / median / p75; salary_low/high = p25/p75 rounded to 1000;
- slugs with fewer than --min-n salaries are SKIPPED (we do not publish thin
  data) and keep their current source.

Auth: application token from env (HH_APP_TOKEN; see /etc/astrolab/env on prod).
Run manually, DEV/ops only — the deploy hook never runs it:

    python -m scripts.fetch_ru_facts_hh --compare seed/facts_ru.json \
        --out seed/facts_hh.json [--slugs a,b,c] [--pages 3] [--min-n 30]

Then seed with:  python -m scripts.seed_facts --file seed/facts_hh.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from statistics import median, quantiles

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.hh.ru/vacancies"
UA = "Astrolab/1.0 (diamexx@mail.ru)"
AREA_RUSSIA = "113"
NET_TO_GROSS = 0.87  # 13% personal income tax


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def salaries_for(query: str, token: str, pages: int) -> list[float]:
    """One midpoint per vacancy with a RUR salary, normalized to gross."""
    out: list[float] = []
    for page in range(pages):
        qs = urllib.parse.urlencode(
            {
                "text": query,
                "search_field": "name",
                "only_with_salary": "true",
                "area": AREA_RUSSIA,
                "per_page": "100",
                "page": str(page),
            }
        )
        data = _get(f"{API}?{qs}", token)
        for v in data.get("items", []):
            s = v.get("salary") or {}
            if s.get("currency") != "RUR":
                continue
            lo, hi = s.get("from"), s.get("to")
            val = (lo + hi) / 2 if lo and hi else lo or hi
            if not val:
                continue
            if s.get("gross") is False:
                val = val / NET_TO_GROSS
            out.append(float(val))
        if page + 1 >= int(data.get("pages", 0)):
            break
        time.sleep(0.3)  # polite pacing, app-token rate limits
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queries", default=str(ROOT / "seed" / "hh_queries.json"))
    ap.add_argument("--compare", default=str(ROOT / "seed" / "facts_ru.json"))
    ap.add_argument("--out", default=str(ROOT / "seed" / "facts_hh.json"))
    ap.add_argument("--slugs", default="", help="comma-separated subset")
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--min-n", type=int, default=30)
    args = ap.parse_args()

    token = os.environ.get("HH_APP_TOKEN", "")
    if not token:
        sys.exit("HH_APP_TOKEN is not set (source /etc/astrolab/env)")

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
    print(f"{'slug':34} {'n':>5}  {'hh p25-p75 (gross)':>22}  {'baseline low-high':>20}  ratio")
    for slug, cfg in queries.items():
        if subset and slug not in subset:
            continue
        vals = salaries_for(cfg["query"], token, args.pages)
        n = len(vals)
        if n < args.min_n:
            skipped.append((slug, n))
            print(f"{slug:34} {n:>5}  {'-- skipped (thin) --':>22}")
            continue
        q = quantiles(vals, n=4)
        p25, p75 = q[0], q[2]
        lo = int(round(p25 / 1000) * 1000)
        hi = int(round(p75 / 1000) * 1000)
        base = baseline.get(slug) or {}
        b_lo, b_hi = base.get("salary_low"), base.get("salary_high")
        ratio = ""
        if b_lo and b_hi:
            ratio = f"{((lo + hi) / 2) / ((b_lo + b_hi) / 2):.2f}"
        print(f"{slug:34} {n:>5}  {lo:>10,}-{hi:<11,}  {str(b_lo):>9}-{str(b_hi):<10} {ratio}")
        rows.append(
            {
                "slug": slug,
                "salary_low": lo,
                "salary_high": hi,
                "currency": "RUB",
                "period": "month",
                # keep the existing curated demand note (script source must stay
                # Cyrillic-free, so we cannot generate RU text here)
                "demand_note": base.get("demand_note"),
                "confidence": "estimate",
                "n": n,
                "median": int(median(vals)),
            }
        )
        time.sleep(0.3)

    # same top-level contract as facts_ru.json — seed_facts consumes it as-is
    out = {
        "country": "RU",
        "source_key": "hh-vacancies",
        "source_name": "hh.ru live vacancy salary analysis (p25-p75, gross, Russia-wide)",
        "source_url": "https://hh.ru",
        "as_of_date": today,
        "facts": rows,
    }
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nwritten {args.out}: {len(rows)} facts, skipped {len(skipped)} thin: "
          f"{[s for s, _ in skipped][:12]}")


if __name__ == "__main__":
    main()
