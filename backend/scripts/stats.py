"""Print the assessment funnel from the DB.

    python -m scripts.stats            # human-readable
    python -m scripts.stats --json     # raw JSON

No extra tracking needed — it's a pure query over assessment_sessions + answers.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from app.db import SessionLocal
from app.services.stats import compute_funnel


def _bar(count: int, top: int, width: int = 28) -> str:
    filled = int(round((count / top) * width)) if top else 0
    return "#" * filled + "-" * (width - filled)


def _print(f: dict) -> None:
    t = f["totals"]
    print("=" * 52)
    print(f"ASSESSMENT FUNNEL  (as of {f['as_of'][:19]})")
    print("=" * 52)
    print(
        f"sessions: {t['sessions']}   completed: {t['completed']}   "
        f"abandoned: {t['abandoned']}   completion: {t['completion_rate'] * 100:.1f}%"
    )
    print("\nfunnel (unique sessions reaching each step):")
    top = f["funnel"][0]["count"] or 1
    for s in f["funnel"]:
        drop = s.get("dropoff", 0)
        drop_s = f"   (-{drop})" if drop else ""
        print(f"  {s['stage']:<20} {s['count']:>5}  {_bar(s['count'], top)}{drop_s}")
    pr = f["post_result"]
    print(
        f"\npost-result: enriched {pr['enriched']} · interview {pr['interview']} · "
        f"shared {pr['shared']} · saved to account {pr['saved_to_account']}"
    )
    av = f["adults_vs_teens"]
    print(
        f"\nadults: {av['adult']['started']} started / {av['adult']['completed']} done   "
        f"teens: {av['teen']['started']} started / {av['teen']['completed']} done"
    )
    if f["by_age_band"]:
        print("\nby age band:")
        for band, v in sorted(f["by_age_band"].items()):
            print(f"  {band:<8} {v['started']:>4} started  {v['completed']:>4} completed")
    r = f["recent"]
    print(
        f"\nrecent: 7d {r['started_7d']} started / {r['completed_7d']} done   "
        f"30d {r['started_30d']} started / {r['completed_30d']} done"
    )
    print("=" * 52)


async def run(as_json: bool) -> None:
    async with SessionLocal() as s:
        f = await compute_funnel(s)
    if as_json:
        print(json.dumps(f, ensure_ascii=False, indent=2))
    else:
        _print(f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args.json))


if __name__ == "__main__":
    main()
