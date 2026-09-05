"""Commitments router — TRD §4.1, §5.

POST /commitments          — create commitment
GET  /commitments/{id}     — detail
GET  /commitments          — list/filter
"""

import hashlib
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.commitment import Commitment, CommitmentJuror, CommitmentStatus
from app.models.evidence import Evidence
from app.schemas import CommitmentCreate, CommitmentResponse, CommitmentListResponse
from app.services.falsifiability import check_falsifiability

router = APIRouter(prefix="/commitments", tags=["commitments"])


def compute_content_hash(title: str, description: str | None, condition: str, deadline: datetime) -> str:
    """sha256(title + description + condition + deadline) — TRD §3."""
    raw = f"{title}|{description or ''}|{condition}|{deadline.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def commitment_to_response(commitment: Commitment) -> CommitmentResponse:
    """Convert ORM model to response schema."""
    return CommitmentResponse(
        id=commitment.id,
        author_id=commitment.author_id,
        title=commitment.title,
        description=commitment.description,
        measurable_condition=commitment.measurable_condition,
        deadline=commitment.deadline,
        status=commitment.status.value,
        content_hash=commitment.content_hash,
        created_at=commitment.created_at,
        resolved_at=commitment.resolved_at,
        author=None,
        juror_count=len(commitment.jurors) if commitment.jurors else 0,
        evidence_count=len(commitment.evidence) if commitment.evidence else 0,
    )


@router.post("", response_model=CommitmentResponse, status_code=status.HTTP_201_CREATED)
async def create_commitment(
    req: CommitmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new commitment — TRD §4.1.

    1. Calls falsifiability check on measurable_condition
    2. Validates juror handles (2-5, must exist, can't include author)
    3. Computes content_hash
    4. Inserts commitment + commitment_jurors rows
    """
    # Falsifiability check — TRD §4.1 step 2
    check = await check_falsifiability(req.measurable_condition)
    if not check.is_falsifiable:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Commitment condition is not falsifiable: {check.reason}",
        )

    # Validate deadline is in the future
    if req.deadline <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Deadline must be in the future",
        )

    # Validate juror handles — must exist, can't include author
    juror_users = []
    for handle in req.juror_handles:
        if handle == current_user.handle:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You cannot be your own juror",
            )
        result = await db.execute(select(User).where(User.handle == handle))
        juror = result.scalar_one_or_none()
        if not juror:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Juror with handle '{handle}' not found",
            )
        juror_users.append(juror)

    # Compute content hash — TRD §3
    content_hash = compute_content_hash(
        req.title, req.description, req.measurable_condition, req.deadline
    )

    # Create commitment
    commitment = Commitment(
        author_id=current_user.id,
        title=req.title,
        description=req.description,
        measurable_condition=req.measurable_condition,
        deadline=req.deadline,
        content_hash=content_hash,
    )
    db.add(commitment)
    await db.flush()  # Get the ID

    # Create juror assignments
    for juror in juror_users:
        db.add(CommitmentJuror(
            commitment_id=commitment.id,
            juror_id=juror.id,
        ))
        
        # Create notification for juror
        from app.models.notification import Notification, NotificationType
        db.add(Notification(
            user_id=juror.id,
            type=NotificationType.INVITE,
            message=f"You have been invited to be a juror for '{req.title}' by @{current_user.handle}."
        ))

    await db.commit()
    await db.refresh(commitment)

    return commitment_to_response(commitment)


@router.get("/{commitment_id}", response_model=CommitmentResponse)
async def get_commitment(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get commitment detail — public endpoint."""
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")

    return commitment_to_response(commitment)


@router.get("", response_model=CommitmentListResponse)
async def list_commitments(
    author: str | None = Query(None, description="Filter by author handle"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List/filter commitments — public endpoint."""
    query = select(Commitment)

    if author:
        # Look up author by handle
        author_result = await db.execute(select(User).where(User.handle == author))
        author_user = author_result.scalar_one_or_none()
        if author_user:
            query = query.where(Commitment.author_id == author_user.id)
        else:
            return CommitmentListResponse(commitments=[], total=0)

    if status_filter:
        try:
            status_enum = CommitmentStatus(status_filter)
            query = query.where(Commitment.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch page
    query = query.order_by(Commitment.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    commitments = list(result.scalars().all())

    return CommitmentListResponse(
        commitments=[commitment_to_response(c) for c in commitments],
        total=total,
    )
