"""DB-backed test (CI only): N4 'try it this week' plan — the next_steps service,
plan-item toggle/upsert + validation, and the grouped GET payload.

The plan endpoints require an authenticated user, so we call the route functions
directly with a User + session (bypassing the cookie dependency) rather than over
HTTP."""

from __future__ import annotations

import uuid

import pytest
from app.api.account import PlanToggleIn, my_plan, toggle_plan_step
from app.db import SessionLocal
from app.etl.ingest import upsert_draft
from app.etl.schema import OccupationDraft
from app.models import Occupation, PlanItem, User
from app.services.next_steps import audience_for, resolve_steps
from fastapi import HTTPException
from sqlalchemy import delete, select

from tests.conftest import requires_db

pytestmark = requires_db


def test_resolve_steps_shape() -> None:
    # 3 generic + 1 field-specific = 4; a course link points at the locale's site.
    steps = resolve_steps("tech", "teen", "ru", "Разработчик")
    assert [s["idx"] for s in steps] == [0, 1, 2, 3]
    assert any(s["url"] and "stepik.org" in s["url"] for s in steps)
    en = resolve_steps("tech", "adult", "en", "Software developer")
    assert any(s["url"] and "coursera.org" in s["url"] for s in en)
    assert audience_for("14-16") == "teen" and audience_for("24+") == "adult"


async def test_plan_toggle_and_get() -> None:
    async with SessionLocal() as s:
        await upsert_draft(
            s,
            OccupationDraft(
                slug="plan-occ",
                field_tag="tech",
                riasec={"I": 0.9},
                i18n={"ru": {"title": "T", "summary": "s", "day_in_life": "d", "who_fits": "w"}},
            ),
        )
        user = User(email=f"plan-{uuid.uuid4()}@example.com")
        s.add(user)
        await s.commit()
        occ = (
            await s.execute(select(Occupation).where(Occupation.slug == "plan-occ"))
        ).scalars().first()
        assert occ is not None
        occ_id = occ.id
        uid = user.id

    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.id == uid))).scalars().first()
        assert user is not None

        # bad audience / out-of-range step -> 422
        for bad in (PlanToggleIn(slug="plan-occ", step_idx=0, audience="nope"),
                    PlanToggleIn(slug="plan-occ", step_idx=9, audience="teen")):
            with pytest.raises(HTTPException) as ei:
                await toggle_plan_step(bad, user, s)
            assert ei.value.status_code == 422

        # first click saves + marks done; second flips it off
        r1 = await toggle_plan_step(
            PlanToggleIn(slug="plan-occ", step_idx=0, audience="teen"), user, s
        )
        assert r1["done"] is True
        r2 = await toggle_plan_step(
            PlanToggleIn(slug="plan-occ", step_idx=0, audience="teen"), user, s
        )
        assert r2["done"] is False
        # a different step
        await toggle_plan_step(
            PlanToggleIn(slug="plan-occ", step_idx=1, audience="teen"), user, s
        )

        rows = (
            await s.execute(select(PlanItem).where(PlanItem.user_id == uid))
        ).scalars().all()
        assert len(rows) == 2  # upsert, not duplicated

        plan = await my_plan("ru", user, s)
        assert len(plan["plans"]) == 1
        grp = plan["plans"][0]
        assert grp["slug"] == "plan-occ" and grp["audience"] == "teen"
        assert {st["idx"] for st in grp["steps"]} == {0, 1}  # only saved steps
        assert all("text" in st and "done" in st for st in grp["steps"])

    async with SessionLocal() as s:
        await s.execute(delete(User).where(User.id == uid))
        await s.execute(delete(Occupation).where(Occupation.id == occ_id))
        await s.commit()
