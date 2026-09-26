"""Users router — TRD §5.

GET /users/{handle}                   — public profile + reputation
GET /users/{handle}/reputation-history — reputation events list
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.commitment import Commitment, CommitmentStatus, CommitmentJuror
from app.models.evidence import Evidence
from app.models.vote import Vote, VoteChoice
from app.models.reputation import ReputationEvent
from app.schemas import UserPublic, ReputationEventResponse, ReputationHistoryResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search", response_model=list[dict])
async def search_users(
    q: str,
    db: AsyncSession = Depends(get_db),
):
    """Search users by handle prefix."""
    if not q or len(q) < 2:
        return []
    
    result = await db.execute(
        select(User)
        .where(User.handle.ilike(f"%{q}%"))
        .limit(5)
    )
    users = result.scalars().all()
    return [{"handle": u.handle, "id": str(u.id)} for u in users]


@router.get("/{handle}", response_model=dict)
async def get_user_profile(
    handle: str,
    db: AsyncSession = Depends(get_db),
):
    """Public profile — user info, commitment stats, jury stats."""
    result = await db.execute(select(User).where(User.handle == handle))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Commitment stats
    commitments_total = await db.execute(
        select(func.count())
        .select_from(Commitment)
        .where(Commitment.author_id == user.id)
        .where(Commitment.status.in_([CommitmentStatus.MET, CommitmentStatus.BROKEN]))
    )
    total = commitments_total.scalar() or 0

    commitments_met = await db.execute(
        select(func.count())
        .select_from(Commitment)
        .where(Commitment.author_id == user.id, Commitment.status == CommitmentStatus.MET)
    )
    met = commitments_met.scalar() or 0

    # Jury accuracy
    total_votes_result = await db.execute(
        select(func.count()).select_from(Vote).where(Vote.juror_id == user.id)
    )
    total_votes = total_votes_result.scalar() or 0

    accurate_events = await db.execute(
        select(func.count())
        .select_from(ReputationEvent)
        .where(
            ReputationEvent.user_id == user.id,
            ReputationEvent.reason == "jury_accurate",
        )
    )
    accurate = accurate_events.scalar() or 0

    jury_accuracy = (accurate / total_votes * 100) if total_votes > 0 else 0

    # Partners (users they've shared commitments with as jurors)
    partners_result = await db.execute(
        select(func.count(func.distinct(CommitmentJuror.juror_id)))
        .select_from(CommitmentJuror)
        .join(Commitment, Commitment.id == CommitmentJuror.commitment_id)
        .where(Commitment.author_id == user.id)
    )
    partner_count = partners_result.scalar() or 0

    # India PRD — "Your Impact" stats (distinct definitions):
    # contributions = evidence this user has submitted, across all
    # commitments (not just their own) — PRD §7 evidence flow
    contributions_result = await db.execute(
        select(func.count()).select_from(Evidence).where(
            Evidence.submitter_id == user.id
        )
    )
    contributions = contributions_result.scalar() or 0

    # promises_tracked = commitments this user has authored, any status —
    # everything they've put on the record
    promises_tracked_result = await db.execute(
        select(func.count()).select_from(Commitment).where(
            Commitment.author_id == user.id
        )
    )
    promises_tracked = promises_tracked_result.scalar() or 0

    return {
        "user": UserPublic.model_validate(user).model_dump(),
        "stats": {
            "commitments_total": total,
            "commitments_met": met,
            "completion_rate": round((met / total * 100) if total > 0 else 0, 1),
            "jury_accuracy": round(jury_accuracy, 1),
            "total_votes_cast": total_votes,
            "partner_count": partner_count,
            "evidence_submitted": contributions,
            "commitments_authored": promises_tracked,
        },
    }


@router.get("/{handle}/reputation-history", response_model=ReputationHistoryResponse)
async def get_reputation_history(
    handle: str,
    db: AsyncSession = Depends(get_db),
):
    """Reputation event history for a user."""
    result = await db.execute(select(User).where(User.handle == handle))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    events_result = await db.execute(
        select(ReputationEvent)
        .where(ReputationEvent.user_id == user.id)
        .order_by(ReputationEvent.created_at.desc())
    )
    events = list(events_result.scalars().all())

    return ReputationHistoryResponse(
        events=[
            ReputationEventResponse(
                id=e.id,
                user_id=e.user_id,
                delta=float(e.delta),
                reason=e.reason.value,
                commitment_id=e.commitment_id,
                created_at=e.created_at,
            )
            for e in events
        ],
        current_score=float(user.reputation_score),
    )


@router.get("/{handle}/commitments", response_model=list[dict])
async def get_user_commitments(
    handle: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all commitments authored by a user."""
    # Find user
    result = await db.execute(select(User).where(User.handle == handle))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch commitments
    from app.schemas import CommitmentResponse
    commits_result = await db.execute(
        select(Commitment)
        .where(Commitment.author_id == user.id)
        .order_by(Commitment.created_at.desc())
    )
    commits = commits_result.scalars().all()
    
    return [CommitmentResponse.model_validate(c).model_dump() for c in commits]
