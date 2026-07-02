"""Ingest occupation drafts and (optionally) apply council review verdicts.

    python -m scripts.catalog_ingest --drafts seed/occupations_batch1.json \
                                     [--reviews seed/reviews_batch1.json]

Ingest is idempotent (upsert by slug); nothing is published until a passing
council verdict is applied.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db import SessionLocal
from app.etl.ingest import upsert_draft
from app.etl.review import apply_verdict
from app.etl.schema import OccupationDraft, ReviewVerdict


async def run(drafts_path: str, reviews_path: str | None) -> None:
    drafts = [OccupationDraft(**d) for d in json.loads(Path(drafts_path).read_text("utf-8"))]
    async with SessionLocal() as session:
        for d in drafts:
            await upsert_draft(session, d)
        await session.commit()
        print(f"[ingest] upserted {len(drafts)} drafts")

        if reviews_path:
            verdicts = [
                ReviewVerdict(**v) for v in json.loads(Path(reviews_path).read_text("utf-8"))
            ]
            for v in verdicts:
                status = await apply_verdict(session, v)
                print(f"[review] {status}")
            await session.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", required=True)
    ap.add_argument("--reviews", default=None)
    args = ap.parse_args()
    asyncio.run(run(args.drafts, args.reviews))


if __name__ == "__main__":
    main()
