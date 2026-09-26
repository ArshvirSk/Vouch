"""Votes router — TRD §4.3.

POST /commitments/{id}/vote   — cast vote (jurors only)
GET  /commitments/{id}/votes  — view votes (after resolution only)
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.commitment import Commitment, CommitmentJuror, CommitmentStatus
from app.models.vote import Vote, VoteChoice
from app.schemas import VoteCreate, VoteResponse
from app.services.jury_resolution import resolve_commitment
from app.services.verdict_history import record_snapshot

router = APIRouter(prefix="/commitments", tags=["votes"])


@router.post("/{commitment_id}/vote", response_model=VoteResponse, status_code=status.HTTP_201_CREATED)
async def cast_vote(
    commitment_id: uuid.UUID,
    req: VoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cast a jury vote — TRD §4.3.

    Only invited jurors can vote. One vote per juror enforced by DB constraint.
    When all jurors have voted, triggers resolution.
    """
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")

    # Must be in verification
    if commitment.status != CommitmentStatus.IN_VERIFICATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Commitment is in '{commitment.status.value}' status, not in verification",
        )

    # Must be an invited juror
    juror_check = await db.execute(
        select(CommitmentJuror).where(
            CommitmentJuror.commitment_id == commitment_id,
            CommitmentJuror.juror_id == current_user.id,
        )
    )
    if not juror_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a juror for this commitment",
        )

    # Check if already voted
    existing_vote = await db.execute(
        select(Vote).where(
            Vote.commitment_id == commitment_id,
            Vote.juror_id == current_user.id,
        )
    )
    if existing_vote.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already voted on this commitment",
        )

    # Cast vote
    vote = Vote(
        commitment_id=commitment_id,
        juror_id=current_user.id,
        vote=VoteChoice(req.vote),
        reason=req.reason,
    )
    db.add(vote)
    await db.flush()
    # Stage 2: snapshot the tally after every vote for the history chart.
    await record_snapshot(db, commitment_id, event_label="Juror vote cast", event_type="vote")
    await db.commit()
    await db.refresh(vote)

    # Check if all jurors have voted → trigger resolution
    total_jurors = await db.execute(
        select(CommitmentJuror).where(CommitmentJuror.commitment_id == commitment_id)
    )
    juror_count = len(list(total_jurors.scalars().all()))

    total_votes = await db.execute(
        select(Vote).where(Vote.commitment_id == commitment_id)
    )
    vote_count = len(list(total_votes.scalars().all()))

    if vote_count >= juror_count:
        # All jurors voted — resolve immediately
        await resolve_commitment(db, commitment_id)

    return VoteResponse(
        id=vote.id,
        commitment_id=vote.commitment_id,
        juror_id=vote.juror_id,
        vote=vote.vote.value,
        reason=vote.reason,
        voted_at=vote.voted_at,
    )


@router.get("/{commitment_id}/votes", response_model=list[VoteResponse])
async def get_votes(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get votes for a commitment — visible only after resolution (TRD §5)."""
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")

    # Votes only visible after resolution — prevents anchoring/groupthink (Design §5.4)
    resolved_statuses = {CommitmentStatus.MET, CommitmentStatus.BROKEN, CommitmentStatus.DISPUTED}
    if commitment.status not in resolved_statuses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votes are only visible after commitment is resolved",
        )

    result = await db.execute(
        select(Vote).where(Vote.commitment_id == commitment_id)
    )
    votes = list(result.scalars().all())

    return [
        VoteResponse(
            id=v.id,
            commitment_id=v.commitment_id,
            juror_id=v.juror_id,
            vote=v.vote.value,
            reason=v.reason,
            voted_at=v.voted_at,
        )
        for v in votes
    ]
