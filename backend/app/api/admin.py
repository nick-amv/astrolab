"""Read-only admin endpoints. Gated by a shared secret (ASTROLAB_ADMIN_TOKEN);
disabled entirely (404) when the token is unset."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.services.stats import compute_funnel

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=404, detail="not found")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/stats", dependencies=[Depends(_require_admin)])
async def stats(session: AsyncSession = Depends(get_session)) -> dict:
    """Assessment funnel: started → answered → completed, plus drop-off,
    segments and recent activity."""
    return await compute_funnel(session)
