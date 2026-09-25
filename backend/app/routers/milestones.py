"""Milestones router — Phase 3: Milestone Tracking.

CRUD for a commitment's milestones (author or moderator), juror verification
of submitted milestones, and a public progress view.

Endpoints (all under /commitments/{id}/milestones):
  POST   /commitments/{id}/milestones          — create (author or moderator)
  GET    /commitments/{id}/milestones          — list + progress (public)
  PATCH  /commitments/{id}/milestones/{mid}    — edit (author or moderator)
  DELETE /commitments/{id}/milestones/{mid}    — remove (author or moderator)
  POST   /commitments/{id}/milestones/{mid}/submit  — author claims done
  POST   /commitments/{id}/milestones/{mid}/verify  — juror confirms/rejects
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.commitment import Commitment, CommitmentJuror, CommitmentStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.user import User
from app.services.milestone_service import compute_progress

router = APIRouter(prefix="/commitments", tags=["milestones"])


class MilestoneCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    detail: str | None = None
    position: int = Field(0, ge=0)
    progress_weight: float = Field(1.0, gt=0, le=100)
    target_date: datetime | None = None


class MilestoneUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=300)
    detail: str | None = None
    position: int | None = Field(None, ge=0)
    progress_weight: float | None = Field(None, gt=0, le=100)
    target_date: datetime | None = None


class MilestoneStatusUpdate(BaseModel):
    # Jurors confirm (verified) or reject (back to pending) a submitted milestone
    decision: str = Field(..., pattern="^(verified|pending)$")


class MilestoneResponse(BaseModel):
    id: uuid.UUID
    commitment_id: uuid.UUID
    title: str
    detail: str | None
    position: int
    progress_weight: float
    target_date: datetime | None
    status: str
    verified_at: datetime | None

    model_config = {"from_attributes": True}


class MilestoneListResponse(BaseModel):
    milestones: list[MilestoneResponse]
    progress: float  # 0.0-1.0 weighted completion
    verified_count: int
    total_count: int


def _to_response(m: Milestone) -> MilestoneResponse:
    return MilestoneResponse(
        id=m.id,
        commitment_id=m.commitment_id,
        title=m.title,
        detail=m.detail,
        position=m.position,
        progress_weight=m.progress_weight,
        target_date=m.target_date,
        status=m.status.value,
        verified_at=m.verified_at,
    )


async def _get_commitment(db: AsyncSession, commitment_id: uuid.UUID) -> Commitment:
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return commitment


async def _require_author_or_moderator(
    commitment: Commitment, current_user: User
) -> None:
    if commitment.author_id != current_user.id and not current_user.is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the commitment author or a moderator can manage milestones",
        )


async def _get_milestone(
    db: AsyncSession, commitment_id: uuid.UUID, milestone_id: uuid.UUID
) -> Milestone:
    milestone = await db.get(Milestone, milestone_id)
    if not milestone or milestone.commitment_id != commitment_id:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.post("/{commitment_id}/milestones", response_model=MilestoneListResponse, status_code=status.HTTP_201_CREATED)
async def create_milestone(
    commitment_id: uuid.UUID,
    req: MilestoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a milestone to a commitment (author or moderator)."""
    commitment = await _get_commitment(db, commitment_id)
    await _require_author_or_moderator(commitment, current_user)

    if commitment.status not in (
        CommitmentStatus.OPEN,
        CommitmentStatus.EVIDENCE_SUBMITTED,
        CommitmentStatus.IN_VERIFICATION,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add milestones to a commitment in '{commitment.status.value}' status",
        )

    milestone = Milestone(
        commitment_id=commitment_id,
        title=req.title,
        detail=req.detail,
        position=req.position,
        progress_weight=req.progress_weight,
        target_date=req.target_date,
        status=MilestoneStatus.PENDING,
    )
    db.add(milestone)
    await db.commit()
    return await list_milestones(commitment_id=commitment_id, db=db)


@router.get("/{commitment_id}/milestones", response_model=MilestoneListResponse)
async def list_milestones(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List a commitment's milestones with weighted progress (public)."""
    await _get_commitment(db, commitment_id)
    # Explicit query (not the relationship) — avoids implicit lazy IO in async
    result = await db.execute(
        select(Milestone)
        .where(Milestone.commitment_id == commitment_id)
        .order_by(Milestone.position)
    )
    milestones = list(result.scalars().all())
    verified = [m for m in milestones if m.status == MilestoneStatus.VERIFIED]
    return MilestoneListResponse(
        milestones=[_to_response(m) for m in milestones],
        progress=round(compute_progress(milestones), 4),
        verified_count=len(verified),
        total_count=len(milestones),
    )


@router.patch("/{commitment_id}/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    commitment_id: uuid.UUID,
    milestone_id: uuid.UUID,
    req: MilestoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit a milestone (author or moderator). Only pending milestones can be edited."""
    commitment = await _get_commitment(db, commitment_id)
    await _require_author_or_moderator(commitment, current_user)
    milestone = await _get_milestone(db, commitment_id, milestone_id)

    if milestone.status != MilestoneStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending milestones can be edited",
        )

    if req.title is not None:
        milestone.title = req.title
    if req.detail is not None:
        milestone.detail = req.detail
    if req.position is not None:
        milestone.position = req.position
    if req.progress_weight is not None:
        milestone.progress_weight = req.progress_weight
    if req.target_date is not None:
        milestone.target_date = req.target_date

    await db.commit()
    await db.refresh(milestone)
    return _to_response(milestone)


@router.delete("/{commitment_id}/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_milestone(
    commitment_id: uuid.UUID,
    milestone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a milestone (author or moderator)."""
    commitment = await _get_commitment(db, commitment_id)
    await _require_author_or_moderator(commitment, current_user)
    milestone = await _get_milestone(db, commitment_id, milestone_id)

    if milestone.status != MilestoneStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending milestones can be deleted",
        )

    await db.delete(milestone)
    await db.commit()


@router.post("/{commitment_id}/milestones/{milestone_id}/submit", response_model=MilestoneResponse)
async def submit_milestone(
    commitment_id: uuid.UUID,
    milestone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Author claims a milestone is complete — moves it to 'submitted' for juror verification."""
    commitment = await _get_commitment(db, commitment_id)
    if commitment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the commitment author can submit milestone progress",
        )
    milestone = await _get_milestone(db, commitment_id, milestone_id)

    if milestone.status not in (MilestoneStatus.PENDING, MilestoneStatus.SUBMITTED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Milestone in '{milestone.status.value}' status cannot be submitted",
        )

    milestone.status = MilestoneStatus.SUBMITTED
    await db.commit()
    await db.refresh(milestone)
    return _to_response(milestone)


@router.post("/{commitment_id}/milestones/{milestone_id}/verify", response_model=MilestoneResponse)
async def verify_milestone(
    commitment_id: uuid.UUID,
    milestone_id: uuid.UUID,
    req: MilestoneStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """A juror confirms ('verified') or rejects ('pending') a submitted milestone.

    The author cannot verify their own milestones; verification requires being
    an assigned juror (or a moderator).
    """
    commitment = await _get_commitment(db, commitment_id)
    milestone = await _get_milestone(db, commitment_id, milestone_id)

    if milestone.status != MilestoneStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only submitted milestones can be verified",
        )
    if commitment.author_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The author cannot verify their own milestone",
        )

    if not current_user.is_moderator:
        juror_check = await db.execute(
            select(CommitmentJuror).where(
                CommitmentJuror.commitment_id == commitment_id,
                CommitmentJuror.juror_id == current_user.id,
            )
        )
        if not juror_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only assigned jurors (or moderators) can verify milestones",
            )

    if req.decision == "verified":
        milestone.status = MilestoneStatus.VERIFIED
        milestone.verified_by_id = current_user.id
        milestone.verified_at = datetime.now(timezone.utc)
    else:
        milestone.status = MilestoneStatus.PENDING

    await db.commit()
    await db.refresh(milestone)
    return _to_response(milestone)
