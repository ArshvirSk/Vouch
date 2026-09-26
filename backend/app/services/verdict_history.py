"""Verdict history recording — Stage 2.

One function, called from every tally-changing path: cast_vote, submit
evidence, and commitment status transitions (deadline worker, jury
resolution). Snapshots are append-only; recording must never break the
calling flow, so failures are swallowed with a log line.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.vote import Vote, VoteChoice
from app.models.verdict_history import VerdictHistory

logger = logging.getLogger(__name__)


async def record_snapshot(
    db: AsyncSession,
    commitment_id,
    *,
    event_label: str | None = None,
    event_type: str = "status",
    juror_count: int | None = None,
) -> None:
    """Append one tally snapshot for the commitment. Never raises."""
    try:
        rows = (await db.execute(
            select(Vote.vote, func.count()).where(Vote.commitment_id == commitment_id).group_by(Vote.vote)
        )).all()
        counts = {vote: n for vote, n in rows}

        if juror_count is None:
            # Caller didn't supply it — count of committed jurors is not
            # cheaply available here; fall back to total votes cast.
            juror_count = sum(counts.values())

        db.add(VerdictHistory(
            commitment_id=commitment_id,
            met_count=counts.get(VoteChoice.MET, 0),
            broken_count=counts.get(VoteChoice.BROKEN, 0),
            abstain_count=counts.get(VoteChoice.ABSTAIN, 0),
            juror_count=juror_count,
            event_label=event_label,
            event_type=event_type,
        ))
        await db.flush()
    except Exception:
        logger.exception("Failed to record verdict history for %s", commitment_id)
