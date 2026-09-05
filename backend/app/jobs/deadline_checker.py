"""Background job: deadline checker — TRD §4.2 step 4.

Runs periodically to:
1. Transition commitments past deadline to 'in_verification'
2. Open the vote window (72h)
3. Auto-resolve commitments whose vote window has expired

In production, this would be a Redis-scheduled job or Celery beat task.
For MVP, it's a function that can be called from a /admin/run-jobs endpoint
or a simple scheduler.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commitment import Commitment, CommitmentStatus
from app.config import get_settings
from app.services.jury_resolution import resolve_commitment


async def check_deadlines(db: AsyncSession) -> dict:
    """Check for commitments past deadline and transition them.

    Returns counts of transitioned commitments.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    vote_window = timedelta(hours=settings.vote_window_hours)

    results = {"transitioned_to_verification": 0, "auto_resolved": 0}

    # 1. Find commitments past deadline that are still open/evidence_submitted
    #    → transition to in_verification
    past_deadline = await db.execute(
        select(Commitment).where(
            Commitment.deadline <= now,
            Commitment.status.in_([
                CommitmentStatus.OPEN,
                CommitmentStatus.EVIDENCE_SUBMITTED,
            ]),
        )
    )
    for commitment in past_deadline.scalars().all():
        # If no evidence was submitted, mark as expired instead
        if commitment.status == CommitmentStatus.OPEN and not commitment.evidence:
            commitment.status = CommitmentStatus.EXPIRED
            commitment.resolved_at = now
        else:
            commitment.status = CommitmentStatus.IN_VERIFICATION
        results["transitioned_to_verification"] += 1

    await db.commit()

    # 2. Find commitments in_verification where vote window has expired
    #    → auto-resolve with whatever votes exist (auto-abstain for non-voters)
    vote_window_expired = await db.execute(
        select(Commitment).where(
            Commitment.status == CommitmentStatus.IN_VERIFICATION,
            Commitment.deadline + vote_window <= now,
        )
    )
    for commitment in vote_window_expired.scalars().all():
        try:
            await resolve_commitment(db, commitment.id)
            results["auto_resolved"] += 1
        except ValueError:
            # Already resolved or invalid state — skip
            pass

    return results
