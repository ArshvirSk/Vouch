import logging
from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models.commitment import Commitment, CommitmentStatus, JuryPool, CommitmentJuror
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.services.jury_weighting import juror_weight, weighted_pick_without_replacement

logger = logging.getLogger(__name__)

# Minimum share of the target jury size that must be filled from the pool
# before the pool is considered viable (0.6 → a pool of 2 can fill a 3-seat
# jury but not a 5-seat one).
MIN_POOL_QUORUM = 0.6


async def select_public_juries():
    """
    Finds public commitments whose deadlines have passed and assigns jurors
    from the JuryPool based on stake/reputation weight.
    """
    logger.info("Starting public jury selection job...")

    async with AsyncSessionLocal() as db:
        # Find public commitments past their deadline that still need jurors:
        # they have a jury_pool_size but no jurors assigned yet.
        stmt = select(Commitment).where(
            Commitment.is_public == True,  # noqa: E712
            Commitment.jury_pool_size.isnot(None),
            Commitment.jury_pool_size > 0,
            Commitment.deadline <= func.now(),
            Commitment.status.in_([CommitmentStatus.OPEN, CommitmentStatus.EVIDENCE_SUBMITTED]),
        )

        result = await db.execute(stmt)
        commitments = result.scalars().all()

        for commitment in commitments:
            # Check if jurors already assigned
            jurors_stmt = select(CommitmentJuror).where(CommitmentJuror.commitment_id == commitment.id)
            existing_jurors = (await db.execute(jurors_stmt)).scalars().all()

            if len(existing_jurors) > 0:
                continue # Already assigned

            # Get the pool with juror reputation for weighting
            pool_stmt = (
                select(JuryPool, User)
                .join(User, User.id == JuryPool.user_id)
                .where(JuryPool.commitment_id == commitment.id)
            )
            pool_rows = (await db.execute(pool_stmt)).all()

            if not pool_rows:
                logger.warning(f"No one joined the jury pool for public commitment {commitment.id}")
                continue

            # ── Reputation-weighted selection (Phase 4) ──
            # Weight = stake + (reputation-normalized bonus). A juror's
            # accumulated accuracy on past juries increases their draw odds,
            # making brigading costly: coordinated fresh accounts carry no
            # reputation and draw like everyone else, while users who have
            # voted accurately in the past are preferentially drawn.
            target = commitment.jury_pool_size
            if len(pool_rows) < max(3, int(target * MIN_POOL_QUORUM)):
                logger.warning(
                    "Pool for commitment %s has %d members (need %d) — skipping until quorum",
                    commitment.id, len(pool_rows), target,
                )
                continue

            candidates = [pool_entry for pool_entry, _ in pool_rows]
            weights = [
                juror_weight(
                    max(0.0, float(pool_entry.staked_amount or 0)),
                    float(juror.reputation_score or 0),
                )
                for pool_entry, juror in pool_rows
            ]

            num_to_select = min(target, len(candidates))
            selected_jurors = weighted_pick_without_replacement(candidates, weights, num_to_select)

            # Assign them
            for pool_entry in selected_jurors:
                db.add(CommitmentJuror(
                    commitment_id=commitment.id,
                    juror_id=pool_entry.user_id,
                ))

                db.add(Notification(
                    user_id=pool_entry.user_id,
                    type=NotificationType.INVITE, # reusing invite type for now
                    message=f"You have been selected from the pool to judge '{commitment.title}'!"
                ))

            logger.info(f"Selected {len(selected_jurors)} jurors for public commitment {commitment.id}")

        await db.commit()
