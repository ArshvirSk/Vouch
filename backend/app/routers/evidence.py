"""Evidence router — TRD §4.2.

POST /commitments/{id}/evidence — submit evidence
"""

import hashlib
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.commitment import Commitment, CommitmentStatus
from app.models.evidence import Evidence, EvidenceType
from app.schemas import EvidenceCreate, EvidenceResponse
from app.services.verdict_history import record_snapshot

router = APIRouter(prefix="/commitments", tags=["evidence"])


@router.post("/{commitment_id}/evidence", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def submit_evidence(
    commitment_id: uuid.UUID,
    req: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit evidence for a commitment — TRD §4.2.

    Allowed any time before deadline (or during short grace window).
    On first evidence, transitions status open → evidence_submitted.
    """
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")

    # Only allow evidence on open or evidence_submitted commitments
    if commitment.status not in (CommitmentStatus.OPEN, CommitmentStatus.EVIDENCE_SUBMITTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit evidence for commitment in '{commitment.status.value}' status",
        )

    # Check deadline (allow 1 hour grace window).
    # Normalize: the DB column is naive UTC, so compare like-for-like.
    grace_hours = 1
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    deadline = commitment.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if now > deadline + timedelta(hours=grace_hours):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence submission deadline has passed",
        )

    # Compute content_hash — TRD §3
    content_hash = hashlib.sha256(req.content.encode()).hexdigest()

    # Create evidence
    evidence = Evidence(
        commitment_id=commitment_id,
        submitter_id=current_user.id,
        type=EvidenceType(req.type),
        content=req.content,
        content_hash=content_hash,
        phase=req.phase,
    )
    db.add(evidence)

    # Transition status on first evidence — TRD §4.2 step 3
    if commitment.status == CommitmentStatus.OPEN:
        commitment.status = CommitmentStatus.EVIDENCE_SUBMITTED

    # Stage 2: snapshot on evidence events for the history chart.
    await record_snapshot(
        db, commitment_id, event_label="Evidence submitted", event_type="evidence"
    )
    await db.commit()
    await db.refresh(evidence)

    return EvidenceResponse(
        id=evidence.id,
        commitment_id=evidence.commitment_id,
        submitter_id=evidence.submitter_id,
        type=evidence.type.value,
        content=evidence.content,
        content_hash=evidence.content_hash,
        phase=evidence.phase,
        submitted_at=evidence.submitted_at,
    )


@router.get("/{commitment_id}/evidence", response_model=list[EvidenceResponse])
async def list_evidence(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all evidence for a commitment — public endpoint."""
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")

    result = await db.execute(
        select(Evidence)
        .where(Evidence.commitment_id == commitment_id)
        .order_by(Evidence.submitted_at.asc())
    )
    evidence_list = list(result.scalars().all())

    return [
        EvidenceResponse(
            id=e.id,
            commitment_id=e.commitment_id,
            submitter_id=e.submitter_id,
            type=e.type.value,
            content=e.content,
            content_hash=e.content_hash,
            phase=e.phase,
            submitted_at=e.submitted_at,
        )
        for e in evidence_list
    ]
