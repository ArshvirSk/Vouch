"""Admin/seed endpoint for testing the full commitment lifecycle.

NOT for production use — enables manual triggering of background jobs
and seeding test data for the complete lifecycle flow.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.jobs.deadline_checker import check_deadlines
from app.jobs.reputation_recompute import run_reputation_recompute
from app.tasks.anchor import anchor_pending_commitments
from app.tasks.jury_selection import select_public_juries
from app.tasks.anchor_reputation import anchor_reputations
from app.services.milestone_service import check_milestones

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/run-jobs")
async def run_background_jobs(db: AsyncSession = Depends(get_db)):
    """Manually trigger background jobs — deadline checker + reputation recompute.

    In production, these would be triggered by Redis/APScheduler/cron.
    """
    deadline_results = await check_deadlines(db)
    reputation_results = await run_reputation_recompute(db)

    return {
        "deadline_checker": deadline_results,
        "reputation_recompute": reputation_results,
    }


@router.post("/run-phase5-jobs")
async def run_phase5_jobs():
    """Manually trigger the Phase 5 background jobs (own sessions):

    - select_public_juries: assigns stake-weighted jurors to public
      commitments whose deadline has passed.
    - anchor_pending_commitments: computes a Merkle root over unanchored
      commitments and anchors it on Polygon.
    """
    await select_public_juries()
    await anchor_pending_commitments()
    return {"status": "ok"}


@router.post("/run-phase3-jobs")
async def run_phase3_jobs():
    """Manually trigger the Phase 3 on-chain jobs (own sessions):

    - anchor_reputations: recomputes reputation scores and publishes
      backend-signed attestations to the VouchReputation contract.
    """
    result = await anchor_reputations()
    milestone_result = await check_milestones()
    return {"status": "ok", "reputation_anchoring": result, "milestone_check": milestone_result}
