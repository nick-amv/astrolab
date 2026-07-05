"""Public occupation catalog API (published rows only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.education import get_education
from app.services.catalog import get_occupation_detail, list_published

router = APIRouter(prefix="/api/occupations", tags=["occupations"])


@router.get("")
async def list_occupations(
    locale: str = Query("ru"),
    country: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    items = await list_published(session, locale, country)
    return {"count": len(items), "items": items}


@router.get("/{slug}")
async def occupation_detail(
    slug: str,
    locale: str = Query("ru"),
    country: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    detail = await get_occupation_detail(session, slug, locale, country)
    if detail is None:
        raise HTTPException(status_code=404, detail="occupation not found")
    return detail


@router.get("/{slug}/education")
async def occupation_education(
    slug: str,
    country: str = Query("RU"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """How to become this occupation in a given country: fields of study + typical
    exam combinations + admission deadlines. RU is curated; other countries return
    available=false (no LLM-generated paths)."""
    return await get_education(session, slug, country)
