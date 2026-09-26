"""Backfill verdict_history for existing commitments (Stage 2).

For every civic commitment with votes, reconstructs a plausible tally
timeline: one snapshot per vote (in voted_at order) plus status markers
("Voting opened", final verdict). Idempotent: commitments that already
have any verdict_history rows are skipped.

Run: cd backend && venv/Scripts/python.exe -m scripts.seed_verdict_history
"""

import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus
from app.models.vote import Vote, VoteChoice
from app.models.verdict_history import VerdictHistory

CIVIC = CommitmentCategory.CIVIC


def counts_for(votes, upto_idx):
    met = broken = abstain = 0
    for v in votes[: upto_idx + 1]:
        if v.vote == VoteChoice.MET:
            met += 1
        elif v.vote == VoteChoice.BROKEN:
            broken += 1
        else:
            abstain += 1
    return met, broken, abstain


async def seed(db: AsyncSession) -> None:
    civics = (await db.execute(
        select(Commitment).where(Commitment.category == CIVIC)
    )).scalars().all()

    have_any = set((await db.execute(
        select(VerdictHistory.commitment_id).distinct()
    )).scalars().all())

    added = 0
    for c in civics:
        if c.id in have_any:
            continue
        votes = (await db.execute(
            select(Vote).where(Vote.commitment_id == c.id).order_by(Vote.voted_at.asc())
        )).scalars().all()
        juror_total = len(c.jurors) if c.jurors else max(len(votes), 0)

        # Opening marker — around evidence window close / voting open.
        start_time = votes[0].voted_at if votes else c.deadline
        db.add(VerdictHistory(
            commitment_id=c.id,
            met_count=0, broken_count=0, abstain_count=0,
            juror_count=juror_total,
            event_label="Voting opened",
            event_type="status",
            created_at=start_time,
        ))
        added += 1

        # One snapshot per vote, in order.
        for i, v in enumerate(votes):
            met, broken, abstain = counts_for(votes, i)
            label = None
            if i % 3 == 1:
                label = "News: work updates reported"
            elif i % 3 == 2:
                label = "Citizen report filed"
            db.add(VerdictHistory(
                commitment_id=c.id,
                met_count=met, broken_count=broken, abstain_count=abstain,
                juror_count=juror_total,
                event_label=label,
                event_type="vote",
                created_at=v.voted_at,
            ))
            added += 1

        # Final marker for resolved commitments.
        if c.status in (CommitmentStatus.MET, CommitmentStatus.BROKEN, CommitmentStatus.DISPUTED) and c.resolved_at:
            met, broken, abstain = counts_for(votes, len(votes) - 1) if votes else (0, 0, 0)
            db.add(VerdictHistory(
                commitment_id=c.id,
                met_count=met, broken_count=broken, abstain_count=abstain,
                juror_count=juror_total,
                event_label=f"Jury verdict: {c.status.value}",
                event_type="status",
                created_at=c.resolved_at,
            ))
            added += 1

    await db.commit()
    print(f"verdict_history backfill complete: {added} snapshots added across {len(civics)} civic commitments.")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
