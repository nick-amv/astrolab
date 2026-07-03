"""Passwordless accounts: email magic-link (DESIGN §6, PRIVACY_MODEL §5).

Flow: POST /request {email} → a single-use magic link is emailed. The link opens
the frontend /auth/verify page, which POSTs the token to /verify → a session
cookie is set. No password is ever stored; only hashed tokens (tokens.py).

Anti-abuse: /request never reveals whether an email exists (always 200), and is
rate-limited per email. Minors: claiming a 14-16 profile requires parental
consent, recorded in consent_records.
"""

from __future__ import annotations

import datetime as dt
import re
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.mail import send_magic_link
from app.models import (
    AssessmentSession,
    AuthToken,
    ConsentRecord,
    Profile,
    User,
)
from app.security.session import (
    clear_session_cookie,
    create_session,
    current_user_optional,
    require_user,
    set_session_cookie,
)
from app.security.tokens import hash_token, new_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
_log = structlog.get_logger("astrolab.auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MINOR_BANDS = {"14-16"}


def _user_out(user: User) -> dict:
    return {"id": str(user.id), "email": user.email}


async def _ensure_consent(session: AsyncSession, user_id: uuid.UUID, kind: str) -> None:
    exists = (
        await session.execute(
            select(ConsentRecord.id).where(
                ConsentRecord.user_id == user_id, ConsentRecord.kind == kind
            )
        )
    ).first()
    if not exists:
        session.add(ConsentRecord(user_id=user_id, kind=kind))


# --------------------------------------------------------------------------- #
# request a magic link
# --------------------------------------------------------------------------- #
class MagicRequestIn(BaseModel):
    email: str
    locale: str = "ru"


@router.post("/request")
async def request_link(
    body: MagicRequestIn, session: AsyncSession = Depends(get_session)
) -> dict:
    email = (body.email or "").strip().lower()[:320]
    locale = body.locale if body.locale in ("ru", "en") else "ru"
    # Always return ok (no account enumeration). Invalid email → no-op.
    if not _EMAIL_RE.match(email):
        return {"ok": True}

    user = (await session.execute(select(User).where(User.email == email))).scalars().first()
    if user is None:
        user = User(email=email)
        session.add(user)
        await session.flush()

    now = dt.datetime.now(dt.UTC)
    window_start = now - dt.timedelta(minutes=settings.magic_link_window_min)
    recent = (
        await session.execute(
            select(func.count())
            .select_from(AuthToken)
            .where(
                AuthToken.user_id == user.id,
                AuthToken.kind == "magic_link",
                AuthToken.created_at >= window_start,
            )
        )
    ).scalar() or 0
    if recent >= settings.magic_link_max_per_window:
        await session.commit()  # persist the (possibly new) user; drop silently
        return {"ok": True}

    raw = new_token()
    session.add(
        AuthToken(
            user_id=user.id,
            kind="magic_link",
            token_hash=hash_token(raw),
            expires_at=now + dt.timedelta(minutes=settings.magic_link_ttl_min),
        )
    )
    await session.commit()

    link = f"{settings.app_base_url}/{locale}/auth/verify?token={raw}"
    try:
        await send_magic_link(email, link, locale)
    except Exception as exc:  # noqa: BLE001 — a mail hiccup must not 500 the user
        _log.warning("auth.mail.failed", error=str(exc))
    return {"ok": True}


# --------------------------------------------------------------------------- #
# verify a magic link → session
# --------------------------------------------------------------------------- #
class VerifyIn(BaseModel):
    token: str


@router.post("/verify")
async def verify(
    body: VerifyIn, response: Response, session: AsyncSession = Depends(get_session)
) -> dict:
    now = dt.datetime.now(dt.UTC)
    row = (
        await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == hash_token(body.token),
                AuthToken.kind == "magic_link",
                AuthToken.expires_at > now,
            )
        )
    ).scalars().first()
    if row is None:
        raise HTTPException(status_code=400, detail="invalid or expired link")

    user = (await session.execute(select(User).where(User.id == row.user_id))).scalars().first()
    if user is None:
        raise HTTPException(status_code=400, detail="invalid link")

    # Single-use: consume the magic token immediately.
    await session.execute(delete(AuthToken).where(AuthToken.id == row.id))
    await _ensure_consent(session, user.id, "data_processing")
    raw = await create_session(session, user.id)
    await session.commit()

    set_session_cookie(response, raw)
    return {"user": _user_out(user)}


# --------------------------------------------------------------------------- #
# session lifecycle
# --------------------------------------------------------------------------- #
@router.post("/logout")
async def logout(
    request: Request, response: Response, session: AsyncSession = Depends(get_session)
) -> dict:
    raw = request.cookies.get(settings.session_cookie_name)
    if raw:
        await session.execute(
            delete(AuthToken).where(
                AuthToken.token_hash == hash_token(raw), AuthToken.kind == "session"
            )
        )
        await session.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
async def whoami(user: User | None = Depends(current_user_optional)) -> dict:
    return {"user": _user_out(user) if user else None}


# --------------------------------------------------------------------------- #
# claim an anonymous result into the account
# --------------------------------------------------------------------------- #
class ClaimIn(BaseModel):
    session_id: str
    parental_consent: bool = False


@router.post("/claim")
async def claim(
    body: ClaimIn,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        sid = uuid.UUID(body.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    ses = (
        await session.execute(select(AssessmentSession).where(AssessmentSession.id == sid))
    ).scalars().first()
    if ses is None:
        raise HTTPException(status_code=404, detail="session not found")
    profile = (
        await session.execute(select(Profile).where(Profile.id == ses.profile_id))
    ).scalars().first()
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    if profile.user_id is not None and profile.user_id != user.id:
        raise HTTPException(status_code=409, detail="already claimed")

    # Minors (14-16): parental consent is required to attach a result to an account.
    if profile.age_band in _MINOR_BANDS and not body.parental_consent:
        raise HTTPException(status_code=422, detail="parental_consent_required")
    if body.parental_consent:
        await _ensure_consent(session, user.id, "parental")

    profile.user_id = user.id
    await session.commit()
    return {"ok": True}
