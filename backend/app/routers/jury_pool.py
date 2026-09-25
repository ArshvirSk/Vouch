"""Jury Pool router — Phase 5.

POST /commitments/{id}/jury-pool   — join the jury pool for a public commitment
GET  /commitments/{id}/jury-pool   — get pool info (size, user membership)
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.commitment import Commitment, JuryPool

router = APIRouter(prefix="/commitments", tags=["jury-pool"])


class JuryPoolResponse(BaseModel):
    pool_size: int
    target_size: int | None
    user_has_joined: bool


class JuryPoolJoinResponse(BaseModel):
    status: str
    pool_size: int


@router.get("/{commitment_id}/jury-pool", response_model=JuryPoolResponse)
async def get_jury_pool(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get jury pool info for a public commitment."""
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    if not commitment.is_public:
        raise HTTPException(status_code=400, detail="This commitment does not have a public jury pool")

    # Count pool members
    count_result = await db.execute(
        select(func.count()).select_from(JuryPool).where(JuryPool.commitment_id == commitment_id)
    )
    pool_size = count_result.scalar() or 0

    return JuryPoolResponse(
        pool_size=pool_size,
        target_size=commitment.jury_pool_size,
        user_has_joined=False,  # Caller must be authenticated to check; default to false
    )


@router.post("/{commitment_id}/jury-pool", response_model=JuryPoolJoinResponse, status_code=status.HTTP_201_CREATED)
async def join_jury_pool(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join the jury pool for a public commitment."""
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    if not commitment.is_public:
        raise HTTPException(status_code=400, detail="This commitment does not have a public jury pool")

    # Can't join your own jury pool
    if commitment.author_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot join the jury pool for your own commitment")

    # Check if already joined
    existing = await db.execute(
        select(JuryPool).where(
            JuryPool.commitment_id == commitment_id,
            JuryPool.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already joined this jury pool")

    # Join pool
    pool_entry = JuryPool(
        commitment_id=commitment_id,
        user_id=current_user.id,
        staked_amount=0.0,  # MVP: no actual staking yet
    )
    db.add(pool_entry)
    await db.commit()

    # Get updated count
    count_result = await db.execute(
        select(func.count()).select_from(JuryPool).where(JuryPool.commitment_id == commitment_id)
    )
    pool_size = count_result.scalar() or 0

    return JuryPoolJoinResponse(status="joined", pool_size=pool_size)
