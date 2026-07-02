"""Right-to-erasure endpoint (Wave 0 acceptance gate: no session data is held
without a working deletion path).

Anonymous users delete by presenting their anon_token; account holders by
user_id (auth wired in Wave 6 — for now the endpoint accepts an explicit
subject and is exercised by tests + the admin path). Deletion cascades through
FK ondelete=CASCADE and is recorded in deletion_log for audit.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import DeletionLog, Profile, User

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


class DeleteRequest(BaseModel):
    anon_token: str | None = None
    user_id: str | None = None


class DeleteResponse(BaseModel):
    deleted: bool
    profiles_removed: int


@router.post("/delete", response_model=DeleteResponse)
async def delete_data(
    req: DeleteRequest,
    session: AsyncSession = Depends(get_session),
) -> DeleteResponse:
    if not req.anon_token and not req.user_id:
        raise HTTPException(status_code=422, detail="anon_token or user_id required")

    now = dt.datetime.now(dt.UTC)
    subject_ref = req.user_id or (req.anon_token or "")[:16]
    session.add(DeletionLog(subject_ref=subject_ref, requested_at=now))

    removed = 0
    if req.anon_token:
        ids = (
            await session.execute(
                select(Profile.id).where(Profile.anon_token == req.anon_token)
            )
        ).scalars().all()
        if ids:
            await session.execute(delete(Profile).where(Profile.id.in_(ids)))
            removed += len(ids)
    if req.user_id:
        # Deleting the user cascades to their profiles, sessions, tokens, etc.
        res = await session.execute(delete(User).where(User.id == req.user_id))
        removed += getattr(res, "rowcount", 0) or 0

    # Mark the audit row complete in the same transaction.
    log_row = (
        await session.execute(
            select(DeletionLog)
            .where(DeletionLog.subject_ref == subject_ref)
            .order_by(DeletionLog.requested_at.desc())
        )
    ).scalars().first()
    if log_row:
        log_row.completed_at = dt.datetime.now(dt.UTC)

    await session.commit()
    return DeleteResponse(deleted=removed > 0, profiles_removed=removed)
