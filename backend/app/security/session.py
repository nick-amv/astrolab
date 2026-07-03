"""Cookie-based session helpers for the magic-link account flow.

A session is a random token; only its SHA-256 hash is stored (auth_tokens,
kind="session"). The raw token lives in an httpOnly, Secure, SameSite=Lax
cookie — never readable by JS, never in the DB. Every request that needs the
user hashes the cookie and looks up a non-expired session row.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import AuthToken, User
from app.security.tokens import hash_token, new_token


async def create_session(session: AsyncSession, user_id: uuid.UUID) -> str:
    """Create a session token row and return the RAW token (store only its hash)."""
    raw = new_token()
    session.add(
        AuthToken(
            user_id=user_id,
            kind="session",
            token_hash=hash_token(raw),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=settings.session_ttl_days),
        )
    )
    return raw


def set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


async def _user_from_cookie(request: Request, session: AsyncSession) -> User | None:
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        return None
    row = (
        await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == hash_token(raw),
                AuthToken.kind == "session",
                AuthToken.expires_at > dt.datetime.now(dt.UTC),
            )
        )
    ).scalars().first()
    if row is None:
        return None
    return (
        await session.execute(select(User).where(User.id == row.user_id))
    ).scalars().first()


async def current_user_optional(
    request: Request, session: AsyncSession = Depends(get_session)
) -> User | None:
    return await _user_from_cookie(request, session)


async def require_user(
    request: Request, session: AsyncSession = Depends(get_session)
) -> User:
    user = await _user_from_cookie(request, session)
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return user
