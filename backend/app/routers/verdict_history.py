"""Verdict history router — Stage 2 of the civic detail redesign.

GET /commitments/{id}/verdict-history — append-only tally snapshots for
the "Public Verdict Over Time" chart.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.commitment import Commitment
from app.models.verdict_history import VerdictHistory

router = APIRouter(prefix="/commitments", tags=["verdict-history"])


@router.get("/{commitment_id}/verdict-history")
async def get_verdict_history(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Tally snapshots over time — public endpoint."""
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")

    result = await db.execute(
        select(VerdictHistory)
        .where(VerdictHistory.commitment_id == commitment_id)
        .order_by(VerdictHistory.created_at.asc(), VerdictHistory.id.asc())
    )
    rows = list(result.scalars().all())

    return {
        "commitment_id": str(commitment_id),
        "juror_count": len(commitment.jurors) if commitment.jurors else 0,
        "snapshots": [
            {
                "id": str(r.id),
                "met": r.met_count,
                "broken": r.broken_count,
                "abstain": r.abstain_count,
                "jurors": r.juror_count,
                "event_label": r.event_label,
                "event_type": r.event_type,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }
