"""Reputation recalculation service — TRD §4.4.

Recomputes users.reputation_score from reputation_events with decay-weighted
window. Designed to run as a scheduled job every 15 minutes (TRD §4.4).

Algorithm (PRD §9):
  reputation_score = (commitments_met / total_commitments) * 100
                     + streak_bonus
                     - dispute_penalty

  With decay: recent events weighted higher than old ones.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.commitment import Commitment, CommitmentStatus
from app.models.reputation import ReputationEvent, ReputationReason
from app.config import get_settings


async def recompute_reputation(db: AsyncSession, user_id: uuid.UUID) -> float:
    """Recompute a single user's reputation score from their event history.

    Uses a decay-weighted sum: each event's delta is multiplied by
    decay_factor^(index from newest), so recent events matter more.

    Returns the new score.
    """
    settings = get_settings()
    decay = settings.reputation_decay_factor

    # Fetch all reputation events for this user, newest first
    result = await db.execute(
        select(ReputationEvent)
        .where(ReputationEvent.user_id == user_id)
        .order_by(ReputationEvent.created_at.desc())
    )
    events = list(result.scalars().all())

    if not events:
        return 0.0

    # Decay-weighted sum
    score = 0.0
    for i, event in enumerate(events):
        weight = decay ** i
        score += float(event.delta) * weight

    # Also compute percentage-based component
    commitment_result = await db.execute(
        select(
            func.count(case((Commitment.status == CommitmentStatus.MET, 1))).label("met"),
            func.count().label("total"),
        )
        .where(Commitment.author_id == user_id)
        .where(Commitment.status.in_([CommitmentStatus.MET, CommitmentStatus.BROKEN]))
    )
    row = commitment_result.one_or_none()

    if row and row.total > 0:
        completion_pct = (row.met / row.total) * 100
    else:
        completion_pct = 0.0

    # Blend: 60% decay-weighted event sum + 40% completion percentage
    # This balances recent behavior (events) with overall track record (percentage)
    final_score = round(0.6 * score + 0.4 * completion_pct, 2)

    # Clamp to reasonable range
    final_score = max(-100.0, min(999.99, final_score))

    # Update user record
    user = await db.get(User, user_id)
    if user:
        user.reputation_score = final_score
        await db.commit()

    return final_score


async def recompute_all_reputations(db: AsyncSession) -> int:
    """Recompute reputation for all users with recent events.

    Returns the number of users updated.
    """
    result = await db.execute(
        select(ReputationEvent.user_id).distinct()
    )
    user_ids = [row[0] for row in result.all()]

    for uid in user_ids:
        await recompute_reputation(db, uid)

    return len(user_ids)
