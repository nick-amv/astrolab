"""Add English (locale='en') i18n rows to the EXISTING question bank.

    python -m scripts.seed_questions_en [--file seed/questions_en.json] [--version N]

Additive and idempotent — NEVER wipes. Matches existing question_bank rows and
attaches / refreshes their `en` translation:

  * block A (RIASEC interest cards) matched by the row's Russian text
  * block B (school subjects)       matched by dimension == subject code
  * block C (values)                skipped — forced-choice pairs render from
                                    message keys, no DB text (see DESIGN-EN §2.1)

Upsert semantics: inserts a missing `en` row, updates it in place if the text
changed (so re-running after a translation fix self-heals prod), leaves it
untouched otherwise. Answers reference question_id, never i18n rows, so this is
safe to run on live data. Targets the latest question-bank version by default —
the one the API actually serves (see _latest_version in api/assessment.py).
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
DEFAULT_SEED = SEED_DIR / "questions_en.json"


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
            print("[seed_questions_en] no question bank present — seed the RU bank first")
            return

        # Row inventory for the target version, with each row's RU text.
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
        a_by_text: dict[str, tuple[UUID, str]] = {}  # ru_text -> (id, dimension)
        b_by_dim: dict[str, UUID] = {}  # subject code -> id
        for qid, block, dim, ru_text in rows:
            if block == "A":
                a_by_text[ru_text] = (qid, dim)
            elif block == "B":
                b_by_dim[dim] = qid

        # Existing EN rows for this version: question_id -> QuestionI18n row.
        en_rows = (
            await s.execute(
                select(QuestionI18n)
                .join(QuestionBank, QuestionBank.id == QuestionI18n.question_id)
                .where(QuestionBank.version == version, QuestionI18n.locale == "en")
            )
        ).scalars().all()
        en_by_qid = {r.question_id: r for r in en_rows}

        inserted = updated = skipped = 0
        missing: list[str] = []

        def upsert(qid: UUID, text: str) -> None:
            nonlocal inserted, updated, skipped
            existing = en_by_qid.get(qid)
            if existing is None:
                s.add(QuestionI18n(question_id=qid, locale="en", text=text))
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
                    f"[seed_questions_en] WARN dimension mismatch for {item['ru']!r}: "
                    f"bank={dim} seed={item['dimension']}"
                )
            upsert(qid, item["en"])

        for item in data["subjects"]:
            qid = b_by_dim.get(item["code"])
            if qid is None:
                missing.append(f"B/{item['code']}")
                continue
            upsert(qid, item["en"])

        await s.commit()
        print(
            f"[seed_questions_en] version {version}: "
            f"+{inserted} inserted, ~{updated} updated, ={skipped} unchanged"
        )
        if missing:
            print(f"[seed_questions_en] UNMATCHED ({len(missing)}): " + "; ".join(missing))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT_SEED))
    ap.add_argument(
        "--version", type=int, default=None, help="target bank version (default: latest)"
    )
    args = ap.parse_args()
    asyncio.run(run(Path(args.file), args.version))


if __name__ == "__main__":
    main()
