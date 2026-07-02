"""Liveness + readiness. /api/health never touches the DB (used by Caddy /
systemd health checks); /api/health/ready verifies the DB round-trips."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health() -> dict:
    return {"status": "ok", "service": "astrolab-api", "env": settings.environment}


@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict:
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
