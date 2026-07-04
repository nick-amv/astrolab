"""DB-backed integration test for the magic-link account flow (CI only).

Exercises request → verify → me → claim (incl. the minor parental-consent gate)
→ delete, driving the real ASGI app against the migrated Postgres.
"""

from __future__ import annotations

import datetime as dt
import uuid

import httpx
from app.db import SessionLocal
from app.main import app
from app.models import AuthToken, ConsentRecord, Profile, User
from app.security.tokens import hash_token
from sqlalchemy import delete, select

from tests.conftest import requires_db

pytestmark = requires_db


def _client() -> httpx.AsyncClient:
    # https so httpx sends the Secure session cookie back (session_cookie_secure
    # defaults True); over http:// the cookie is dropped and /me sees no session.
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    )


async def _seed_magic_token(email: str, raw: str) -> uuid.UUID:
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.email == email))).scalars().first()
        if user is None:
            user = User(email=email)
            s.add(user)
            await s.flush()
        s.add(
            AuthToken(
                user_id=user.id,
                kind="magic_link",
                token_hash=hash_token(raw),
                expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(minutes=30),
            )
        )
        await s.commit()
        return user.id


async def _new_anon_session(age_band: str) -> str:
    """Create an anonymous scored-ish session, return its id."""
    from app.models import AssessmentSession

    async with SessionLocal() as s:
        p = Profile(anon_token=f"anon-{uuid.uuid4()}", age_band=age_band, locale="ru")
        s.add(p)
        await s.flush()
        ses = AssessmentSession(
            profile_id=p.id, question_bank_version=1, scoring_version=1, status="completed"
        )
        s.add(ses)
        await s.commit()
        return str(ses.id)


async def test_magic_link_request_is_enumeration_safe() -> None:
    async with _client() as c:
        r = await c.post("/api/auth/request", json={"email": "not an email"})
        assert r.status_code == 200 and r.json()["ok"] is True
        r = await c.post("/api/auth/request", json={"email": "real@example.com"})
        assert r.status_code == 200 and r.json()["ok"] is True


async def test_verify_creates_session_and_claims() -> None:
    email = f"u-{uuid.uuid4().hex[:8]}@example.com"
    raw = "raw-" + uuid.uuid4().hex
    user_id = await _seed_magic_token(email, raw)

    async with _client() as c:
        # bad token rejected
        assert (await c.post("/api/auth/verify", json={"token": "nope"})).status_code == 400
        # valid token → session cookie + user
        r = await c.post("/api/auth/verify", json={"token": raw})
        assert r.status_code == 200
        assert r.json()["user"]["email"] == email
        # single-use: the magic token is consumed
        assert (await c.post("/api/auth/verify", json={"token": raw})).status_code == 400
        # session cookie now identifies the user
        me = await c.get("/api/auth/me")
        assert me.json()["user"]["email"] == email

        # adult session claims without consent
        adult_sid = await _new_anon_session("24+")
        assert (await c.post("/api/auth/claim", json={"session_id": adult_sid})).status_code == 200

        # minor session needs parental consent
        minor_sid = await _new_anon_session("14-16")
        r = await c.post("/api/auth/claim", json={"session_id": minor_sid})
        assert r.status_code == 422
        r = await c.post(
            "/api/auth/claim", json={"session_id": minor_sid, "parental_consent": True}
        )
        assert r.status_code == 200

    async with SessionLocal() as s:
        claimed = (
            await s.execute(select(Profile).where(Profile.user_id == user_id))
        ).scalars().all()
        assert len(claimed) == 2  # both anon profiles now belong to the user
        kinds = {
            r for (r,) in (
                await s.execute(
                    select(ConsentRecord.kind).where(ConsentRecord.user_id == user_id)
                )
            ).all()
        }
        assert "data_processing" in kinds and "parental" in kinds
        # cleanup
        await s.execute(delete(User).where(User.id == user_id))
        await s.commit()


async def test_me_requires_auth() -> None:
    async with _client() as c:
        assert (await c.get("/api/me/results")).status_code == 401
        assert (await c.post("/api/me/delete")).status_code == 401
