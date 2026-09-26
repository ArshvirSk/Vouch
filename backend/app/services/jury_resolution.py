"""Jury resolution service — TRD §4.3 + §4.4.

Handles:
- Determining verdict from jury votes (majority → met/broken, tie → disputed)
- Creating reputation events for author and jurors
- Updating commitment status
"""

import uuid
from datetime import datetime, timezone
from collections import Counter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commitment import Commitment, CommitmentStatus, CommitmentJuror
from app.models.vote import Vote, VoteChoice
from app.models.reputation import ReputationEvent, ReputationReason
from app.services.verdict_history import record_snapshot


# Reputation deltas — kept simple and explainable per PRD §9
AUTHOR_MET_DELTA = 5.0
AUTHOR_BROKEN_DELTA = -5.0
JUROR_ACCURATE_DELTA = 2.0
JUROR_INACCURATE_DELTA = -2.0


async def resolve_commitment(
    db: AsyncSession,
    commitment_id: uuid.UUID,
) -> CommitmentStatus:
    """Run resolution logic for a commitment whose vote window has closed
    or all jurors have voted.

    Returns the final status (met/broken/disputed).
    """
    # Fetch commitment
    commitment = await db.get(Commitment, commitment_id)
    if not commitment:
        raise ValueError(f"Commitment {commitment_id} not found")

    if commitment.status not in (CommitmentStatus.IN_VERIFICATION,):
        raise ValueError(
            f"Commitment {commitment_id} is in status {commitment.status}, "
            "not eligible for resolution"
        )

    # Fetch all votes for this commitment
    votes_result = await db.execute(
        select(Vote).where(Vote.commitment_id == commitment_id)
    )
    votes = list(votes_result.scalars().all())

    # Count votes (exclude abstains from verdict calculation)
    vote_counts = Counter()
    for v in votes:
        if v.vote != VoteChoice.ABSTAIN:
            vote_counts[v.vote] += 1

    met_count = vote_counts.get(VoteChoice.MET, 0)
    broken_count = vote_counts.get(VoteChoice.BROKEN, 0)

    # Determine verdict — TRD §4.3
    # resolved_at is a naive-UTC column, so keep the datetime naive
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if met_count > broken_count:
        verdict = CommitmentStatus.MET
    elif broken_count > met_count:
        verdict = CommitmentStatus.BROKEN
    else:
        # Tie → disputed (escalate to author + all jurors for discussion)
        verdict = CommitmentStatus.DISPUTED

    # Update commitment
    commitment.status = verdict
    commitment.resolved_at = now

    # Stage 2: final tally marker for the verdict-over-time chart.
    await record_snapshot(
        db, commitment_id,
        event_label=f"Jury verdict: {verdict.value}",
        event_type="status",
    )

    # Create reputation events — TRD §4.4
    if verdict in (CommitmentStatus.MET, CommitmentStatus.BROKEN):
        # Author reputation
        author_delta = AUTHOR_MET_DELTA if verdict == CommitmentStatus.MET else AUTHOR_BROKEN_DELTA
        author_reason = (
            ReputationReason.COMMITMENT_KEPT
            if verdict == CommitmentStatus.MET
            else ReputationReason.COMMITMENT_BROKEN
        )
        db.add(ReputationEvent(
            user_id=commitment.author_id,
            delta=author_delta,
            reason=author_reason,
            commitment_id=commitment_id,
        ))
        
        # Streak logic
        from app.models.user import User
        author = await db.get(User, commitment.author_id)
        if author:
            if verdict == CommitmentStatus.MET:
                author.current_streak += 1
                if author.current_streak > author.longest_streak:
                    author.longest_streak = author.current_streak
            else:
                author.current_streak = 0

        # Juror reputation — accurate if vote matches verdict, inaccurate otherwise
        # Abstaining jurors get no reputation event (auto-abstain decision)
        for v in votes:
            if v.vote == VoteChoice.ABSTAIN:
                continue

            is_accurate = (
                (v.vote == VoteChoice.MET and verdict == CommitmentStatus.MET)
                or (v.vote == VoteChoice.BROKEN and verdict == CommitmentStatus.BROKEN)
            )
            db.add(ReputationEvent(
                user_id=v.juror_id,
                delta=JUROR_ACCURATE_DELTA if is_accurate else JUROR_INACCURATE_DELTA,
                reason=ReputationReason.JURY_ACCURATE if is_accurate else ReputationReason.JURY_INACCURATE,
                commitment_id=commitment_id,
            ))

        # Notify author
        from app.models.notification import Notification, NotificationType
        db.add(Notification(
            user_id=commitment.author_id,
            type=NotificationType.RESOLUTION,
            message=f"Your commitment '{commitment.title}' was resolved as {verdict.value} by the jury."
        ))

    await db.commit()
    return verdict
