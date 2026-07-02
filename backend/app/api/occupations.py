"""Public occupation catalog API (published rows only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.services.catalog import get_occupation_detail, list_published

router = APIRouter(prefix="/api/occupations", tags=["occupations"])


@router.get("")
async def list_occupations(
    locale: str = Query("ru"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    items = await list_published(session, locale)
    return {"count": len(items), "items": items}


@router.get("/{slug}")
async def occupation_detail(
    slug: str,
    locale: str = Query("ru"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    detail = await get_occupation_detail(session, slug, locale)
    if detail is None:
        raise HTTPException(status_code=404, detail="occupation not found")
    return detail
