"""Add German (locale='de') i18n rows to the EXISTING question bank (DE-1).

    python -m scripts.seed_questions_de [--file seed/questions_de.json] [--version N]

Same contract as seed_questions_es (additive, idempotent, never wipes):
  * block A (RIASEC interest cards) matched by the row's Russian text
  * block B (school subjects)       matched by dimension == subject code
  * block C (values)                skipped — forced-choice pairs render from
                                    message keys, no DB text
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from app.db import SessionLocal
from app.models import QuestionBank, QuestionI18n
from sqlalchemy import select

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
DEFAULT_SEED = SEED_DIR / "questions_de.json"
LOCALE = "de"


async def run(seed_path: Path, version: int | None) -> None:
    data = json.loads(seed_path.read_text("utf-8"))

    async with SessionLocal() as s:
        if version is None:
            version = (
                await s.execute(
                    select(QuestionBank.version).order_by(QuestionBank.version.desc()).limit(1)
                )
            ).scalars().first()
        if version is None:
            print("[seed_questions_de] no question bank present — seed the RU bank first")
            return

        rows = (
            await s.execute(
                select(
                    QuestionBank.id,
                    QuestionBank.block,
                    QuestionBank.dimension,
                    QuestionI18n.text,
                )
                .join(
                    QuestionI18n,
                    (QuestionI18n.question_id == QuestionBank.id)
                    & (QuestionI18n.locale == "ru"),
                )
                .where(QuestionBank.version == version)
            )
        ).all()
        a_by_text: dict[str, tuple[UUID, str]] = {}
        b_by_dim: dict[str, UUID] = {}
        for qid, block, dim, ru_text in rows:
            if block == "A":
                a_by_text[ru_text] = (qid, dim)
            elif block == "B":
                b_by_dim[dim] = qid

        de_rows = (
            await s.execute(
                select(QuestionI18n)
                .join(QuestionBank, QuestionBank.id == QuestionI18n.question_id)
                .where(QuestionBank.version == version, QuestionI18n.locale == LOCALE)
            )
        ).scalars().all()
        de_by_qid = {r.question_id: r for r in de_rows}

        inserted = updated = skipped = 0
        missing: list[str] = []

        def upsert(qid: UUID, text: str) -> None:
            nonlocal inserted, updated, skipped
            existing = de_by_qid.get(qid)
            if existing is None:
                s.add(QuestionI18n(question_id=qid, locale=LOCALE, text=text))
                inserted += 1
            elif existing.text != text:
                existing.text = text
                updated += 1
            else:
                skipped += 1

        for item in data["riasec"]:
            match = a_by_text.get(item["ru"])
            if match is None:
                missing.append(f"A/{item['dimension']}: {item['ru']!r}")
                continue
            qid, dim = match
            if dim != item["dimension"]:
                print(
                    f"[seed_questions_de] WARN dimension mismatch for {item['ru']!r}: "
                    f"bank={dim} seed={item['dimension']}"
                )
            upsert(qid, item["de"])

        for item in data["subjects"]:
            qid = b_by_dim.get(item["code"])
            if qid is None:
                missing.append(f"B/{item['code']}")
                continue
            upsert(qid, item["de"])

        await s.commit()
        print(
            f"[seed_questions_de] version {version}: "
            f"+{inserted} inserted, ~{updated} updated, ={skipped} unchanged"
        )
        if missing:
            print(f"[seed_questions_de] UNMATCHED ({len(missing)}): {missing[:6]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT_SEED))
    ap.add_argument("--version", type=int, default=None)
    args = ap.parse_args()
    asyncio.run(run(Path(args.file), args.version))


if __name__ == "__main__":
    main()
