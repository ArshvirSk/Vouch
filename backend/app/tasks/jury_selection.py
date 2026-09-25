import logging
import random
from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models.commitment import Commitment, CommitmentStatus, JuryPool, CommitmentJuror
from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)

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

            # Get the pool
            pool_stmt = select(JuryPool).where(JuryPool.commitment_id == commitment.id)
            pool = (await db.execute(pool_stmt)).scalars().all()

            if not pool:
                logger.warning(f"No one joined the jury pool for public commitment {commitment.id}")
                continue

            # Stake-weighted selection without replacement: each draw's odds
            # scale with the juror's stake, so whales dominate a single draw
            # but cannot take every seat.
            num_to_select = min(commitment.jury_pool_size, len(pool))
            pool_candidates = list(pool)
            selected_jurors = []
            for _ in range(num_to_select):
                weights = [max(1.0, candidate.staked_amount) for candidate in pool_candidates]
                chosen = random.choices(pool_candidates, weights=weights, k=1)[0]
                selected_jurors.append(chosen)
                pool_candidates.remove(chosen)

            # Assign them
            for candidate in selected_jurors:
                db.add(CommitmentJuror(
                    commitment_id=commitment.id,
                    juror_id=candidate.user_id,
                ))

                db.add(Notification(
                    user_id=candidate.user_id,
                    type=NotificationType.INVITE, # reusing invite type for now
                    message=f"You have been selected from the pool to judge '{commitment.title}'! Your stake is locked."
                ))

            logger.info(f"Selected {len(selected_jurors)} jurors for public commitment {commitment.id}")

        await db.commit()
