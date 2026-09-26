"""Deadline worker — Phase 5.

Background scheduler that runs every 5 minutes to:
1. Expire commitments past their deadline with no evidence.
2. Transition evidence_submitted commitments past deadline to in_verification.
3. Send reminder notifications to jurors.
4. Auto-resolve in_verification commitments whose 72h vote window has
   closed (the resolution step from deadline_checker.check_deadlines —
   without this on the scheduler, in_verification rows pile up forever).
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.commitment import Commitment, CommitmentStatus, CommitmentJuror
from app.models.notification import Notification, NotificationType
from app.services.jury_resolution import resolve_commitment
from app.services.verdict_history import record_snapshot

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
            # Stage 2: "Voting opened" marker for the verdict-over-time chart
            await record_snapshot(
                db, c.id, event_label="Voting opened", event_type="status", juror_count=0
            )

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

        # 3. Auto-resolve in_verification commitments whose vote window has
        # expired — resolve_commitment commits per commitment.
        vote_window = timedelta(hours=get_settings().vote_window_hours)
        vote_window_expired = await db.execute(
            select(Commitment).where(
                Commitment.status == CommitmentStatus.IN_VERIFICATION,
                Commitment.deadline + vote_window <= now,
            )
        )
        resolved = 0
        for c in vote_window_expired.scalars().all():
            try:
                await resolve_commitment(db, c.id)
                await record_snapshot(
                    db, c.id,
                    event_label=f"Auto-resolved after vote window ({c.status.value})",
                    event_type="status",
                )
                resolved += 1
            except ValueError:
                # Already resolved or invalid state — skip
                pass
        if resolved:
            logger.info("Auto-resolved %d commitments after vote window", resolved)
