"""Milestone tracking service — Phase 3.

Ongoing milestone checks for commitments:
- compute_progress: weighted completion across a commitment's milestones
- check_milestones (scheduled): notify authors of milestones due within the
  next 72h, and mark past-due pending/submitted milestones as missed
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commitment import Commitment, CommitmentStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)

# Notify authors when a milestone target date is within this window
DUE_SOON_WINDOW = timedelta(hours=72)


def compute_progress(milestones: list[Milestone]) -> float:
    """Weighted progress across milestones (0.0-1.0).

    Verified milestones count fully; missed ones count as zero; pending and
    submitted count as zero progress but still carry weight in the divisor.
    A commitment with no milestones has no meaningful progress — return 0.0.
    """
    if not milestones:
        return 0.0
    total_weight = sum(float(m.progress_weight or 0) for m in milestones)
    if total_weight <= 0:
        return 0.0
    earned = sum(
        float(m.progress_weight or 0)
        for m in milestones
        if m.status == MilestoneStatus.VERIFIED
    )
    return earned / total_weight


def _notify(db: AsyncSession, user_id, message: str) -> None:
    db.add(Notification(
        user_id=user_id,
        type=NotificationType.MILESTONE_DUE,
        message=message,
    ))


async def check_milestones(db: AsyncSession) -> dict:
    """Scheduled pass: reminders for due-soon milestones + overdue marking.

    Only applies to commitments that are still live (open, evidence submitted,
    or in verification). Returns counters for observability.
    """
    now = datetime.now(timezone.utc)
    live_statuses = [
        CommitmentStatus.OPEN,
        CommitmentStatus.EVIDENCE_SUBMITTED,
        CommitmentStatus.IN_VERIFICATION,
    ]

    # 1. Reminders: pending milestones due within the next 72h
    due_soon = await db.execute(
        select(Milestone, Commitment)
        .join(Commitment, Commitment.id == Milestone.commitment_id)
        .where(
            Milestone.status == MilestoneStatus.PENDING,
            Milestone.target_date.isnot(None),
            Milestone.target_date >= now,
            Milestone.target_date <= now + DUE_SOON_WINDOW,
            Commitment.status.in_(live_statuses),
        )
    )
    reminded = 0
    seen: set[uuid.UUID] = set()
    for milestone, commitment in due_soon.all():
        if milestone.id in seen:
            continue
        seen.add(milestone.id)
        _notify(
            db,
            commitment.author_id,
            f"Milestone '{milestone.title}' on '{commitment.title}' is due "
            f"by {milestone.target_date.date().isoformat()}. Submit evidence and mark it complete.",
        )
        reminded += 1

    # 2. Overdue: pending/submitted milestones past their target date → missed
    overdue = await db.execute(
        select(Milestone, Commitment)
        .join(Commitment, Commitment.id == Milestone.commitment_id)
        .where(
            Milestone.status.in_([MilestoneStatus.PENDING, MilestoneStatus.SUBMITTED]),
            Milestone.target_date.isnot(None),
            Milestone.target_date < now,
            Commitment.status.in_(live_statuses),
        )
    )
    missed = 0
    for milestone, commitment in overdue.all():
        milestone.status = MilestoneStatus.MISSED
        _notify(
            db,
            commitment.author_id,
            f"Milestone '{milestone.title}' on '{commitment.title}' was missed "
            f"(target date {milestone.target_date.date().isoformat()}).",
        )
        missed += 1

    if reminded or missed:
        await db.commit()

    logger.info("Milestone check: %d reminders, %d marked missed", reminded, missed)
    return {"reminders_sent": reminded, "milestones_missed": missed}
