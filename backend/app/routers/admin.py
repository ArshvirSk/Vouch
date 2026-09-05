"""Admin/seed endpoint for testing the full commitment lifecycle.

NOT for production use — enables manual triggering of background jobs
and seeding test data for the complete lifecycle flow.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.jobs.deadline_checker import check_deadlines
from app.jobs.reputation_recompute import run_reputation_recompute

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
