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

    # Check deadline (allow 1 hour grace window)
    grace_hours = 1
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    if now > commitment.deadline + timedelta(hours=grace_hours):
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
    )
    db.add(evidence)

    # Transition status on first evidence — TRD §4.2 step 3
    if commitment.status == CommitmentStatus.OPEN:
        commitment.status = CommitmentStatus.EVIDENCE_SUBMITTED

    await db.commit()
    await db.refresh(evidence)

    return EvidenceResponse(
        id=evidence.id,
        commitment_id=evidence.commitment_id,
        submitter_id=evidence.submitter_id,
        type=evidence.type.value,
        content=evidence.content,
        content_hash=evidence.content_hash,
        submitted_at=evidence.submitted_at,
    )
