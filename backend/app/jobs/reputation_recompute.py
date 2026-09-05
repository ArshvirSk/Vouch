"""Background job: reputation recompute — TRD §4.4.

Runs every 15 minutes to recompute users.reputation_score from
reputation_events with decay weighting.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.reputation_service import recompute_all_reputations


async def run_reputation_recompute(db: AsyncSession) -> dict:
    """Recompute all user reputation scores.

    Returns count of users updated.
    """
    count = await recompute_all_reputations(db)
    return {"users_updated": count}
