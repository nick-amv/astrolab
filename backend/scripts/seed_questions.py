"""Seed the question bank (version-pinned) from seed/questions_v1.json.

    python -m scripts.seed_questions [--force]

Idempotent: skips if the version already exists. --force wipes that version
(cascades to question_i18n) and re-inserts. Block A = RIASEC, B = subjects,
C = values (see METHOD.md).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db import SessionLocal
from app.models import QuestionBank, QuestionI18n
from sqlalchemy import delete, select

SEED = Path(__file__).resolve().parent.parent / "seed" / "questions_v1.json"


async def run(force: bool) -> None:
    data = json.loads(SEED.read_text("utf-8"))
    version = int(data["version"])

    async with SessionLocal() as s:
        existing = (
            await s.execute(select(QuestionBank).where(QuestionBank.version == version))
        ).scalars().first()
        if existing and not force:
            print(f"[seed_questions] version {version} already present; use --force to reseed")
            return
        if existing and force:
            await s.execute(delete(QuestionBank).where(QuestionBank.version == version))
            await s.commit()
            print(f"[seed_questions] wiped version {version}")

        n = 0

        async def add(block: str, dimension: str, ru: str, klimov: str | None) -> None:
            nonlocal n
            q = QuestionBank(
                block=block, dimension=dimension, klimov_tag=klimov, version=version, active=True
            )
            s.add(q)
            await s.flush()
            s.add(QuestionI18n(question_id=q.id, locale="ru", text=ru))
            n += 1

        for item in data["riasec"]:
            await add("A", item["dimension"], item["ru"], item.get("klimov"))
        for item in data["subjects"]:
            await add("B", item["code"], item["ru"], None)
        for item in data["values"]:
            await add("C", item["dimension"], item["ru"], None)

        await s.commit()
        print(f"[seed_questions] seeded {n} questions for version {version}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args.force))


if __name__ == "__main__":
    main()
