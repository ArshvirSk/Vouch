"""Backfill before/after image evidence on civic commitments.

Gives every civic commitment with status in (evidence_submitted,
in_verification, met, broken, disputed) a pair of tagged image evidence rows
('before' + 'after') pointing at stable Unsplash photos, so the Stage 1
before/after slider has real content. Idempotent: skips commitments that
already have a 'before' or 'after' phased row.

Run: cd backend && venv/Scripts/python.exe -m scripts.seed_civic_before_after
"""

import asyncio
import hashlib
import sys

sys.path.insert(0, ".")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus
from app.models.evidence import Evidence, EvidenceType
from app.models.user import User

# Stable Unsplash road/infrastructure photos — verified content:
# BEFORE: excavator tearing up a road; AFTER: smooth fresh asphalt.
BEFORE_URL = "https://images.unsplash.com/photo-1503708928676-1cb796a0891e?w=1200&q=70&fit=crop"
AFTER_URL = "https://images.unsplash.com/photo-1600590395815-077ef25797c3?w=1200&q=70&fit=crop"

ELIGIBLE = (
    CommitmentStatus.EVIDENCE_SUBMITTED,
    CommitmentStatus.IN_VERIFICATION,
    CommitmentStatus.MET,
    CommitmentStatus.BROKEN,
    CommitmentStatus.DISPUTED,
)


async def seed(db: AsyncSession) -> None:
    result = await db.execute(
        select(Commitment).where(
            Commitment.category == CommitmentCategory.CIVIC,
            Commitment.status.in_(ELIGIBLE),
        )
    )
    civics = list(result.scalars().all())

    # Any submitter works; prefer each commitment's own author.
    users = (await db.execute(select(User).limit(1))).scalars().all()
    if not users:
        print("No users found — run seed_mumbai first.")
        return
    fallback_user = users[0]

    # Repair pass: rows seeded earlier with the old (wrong-content) URLs.
    stale = await db.execute(
        select(Evidence).where(Evidence.phase.in_(["before", "after"]))
    )
    fixed = 0
    for ev in stale.scalars().all():
        correct = BEFORE_URL if ev.phase == "before" else AFTER_URL
        if ev.content != correct:
            ev.content = correct
            ev.content_hash = hashlib.sha256(f"{ev.commitment_id}-{ev.phase}".encode()).hexdigest()
            fixed += 1

    added = skipped = 0
    for c in civics:
        existing = await db.execute(
            select(Evidence).where(
                Evidence.commitment_id == c.id,
                Evidence.phase.in_(["before", "after"]),
            )
        )
        if existing.scalars().first():
            skipped += 1
            continue

        submitter_id = c.author_id or fallback_user.id
        base = c.created_at
        db.add(Evidence(
            commitment_id=c.id,
            submitter_id=submitter_id,
            type=EvidenceType.IMAGE,
            content=BEFORE_URL,
            content_hash=hashlib.sha256(f"{c.id}-before".encode()).hexdigest(),
            phase="before",
            submitted_at=base,
        ))
        db.add(Evidence(
            commitment_id=c.id,
            submitter_id=submitter_id,
            type=EvidenceType.IMAGE,
            content=AFTER_URL,
            content_hash=hashlib.sha256(f"{c.id}-after".encode()).hexdigest(),
            phase="after",
            submitted_at=base,
        ))
        added += 2

    await db.commit()
    print(
        f"Added {added} phased evidence rows across {len(civics)} civic "
        f"commitments ({skipped} already had pairs, {fixed} stale URLs repaired)."
    )


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
