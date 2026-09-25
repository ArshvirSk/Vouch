"""Deadline worker — Phase 5.

Background scheduler that runs every 5 minutes to:
1. Expire commitments past their deadline with no evidence.
2. Transition evidence_submitted commitments past deadline to in_verification.
3. Send reminder notifications to jurors.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.commitment import Commitment, CommitmentStatus, CommitmentJuror
from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


async def process_deadlines():
    """Main deadline processing loop. Called by APScheduler every 5 minutes."""
    async with AsyncSessionLocal() as db:
        # Use naive UTC datetime to match SQLAlchemy's default DateTime behavior
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        logger.info("Deadline worker running at %s", now.isoformat())

        # 1. Find OPEN commitments past deadline → EXPIRED (no evidence submitted)
        expired_result = await db.execute(
            select(Commitment).where(
                Commitment.status == CommitmentStatus.OPEN,
                Commitment.deadline < now,
            )
        )
        expired_commitments = list(expired_result.scalars().all())

        for c in expired_commitments:
            c.status = CommitmentStatus.EXPIRED
            c.resolved_at = now
            logger.info("Commitment %s expired (no evidence)", c.id)

            # Notify author
            db.add(Notification(
                user_id=c.author_id,
                type=NotificationType.RESOLUTION,
                message=f"Your commitment '{c.title}' has expired — no evidence was submitted before the deadline.",
            ))

        # 2. Find EVIDENCE_SUBMITTED commitments past deadline → IN_VERIFICATION
        verification_result = await db.execute(
            select(Commitment).where(
                Commitment.status == CommitmentStatus.EVIDENCE_SUBMITTED,
                Commitment.deadline < now,
            )
        )
        verification_commitments = list(verification_result.scalars().all())

        for c in verification_commitments:
            c.status = CommitmentStatus.IN_VERIFICATION
            logger.info("Commitment %s moved to in_verification", c.id)

            # Notify all jurors that voting is open
            jurors_result = await db.execute(
                select(CommitmentJuror).where(CommitmentJuror.commitment_id == c.id)
            )
            jurors = list(jurors_result.scalars().all())
            for juror in jurors:
                db.add(Notification(
                    user_id=juror.juror_id,
                    type=NotificationType.VOTE_REMINDER,
                    message=f"Voting is now open for '{c.title}'. Please review the evidence and cast your vote.",
                ))

        if expired_commitments or verification_commitments:
            await db.commit()
            logger.info(
                "Processed %d expired, %d moved to verification",
                len(expired_commitments),
                len(verification_commitments),
            )
        else:
            logger.debug("No commitments to process")
