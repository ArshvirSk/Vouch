"""Phase 3 task — anchor user reputation on-chain.

Recomputes all reputation scores (decay-weighted, TRD §4.4), then publishes a
signed attestation per user to the VouchReputation contract on Polygon Amoy
for users that have a linked wallet address. The on-chain attestation is
verifiable by anyone via the contract's signature check, so a published
reputation does not depend on trusting the backend UI.

Users without a wallet address are skipped (nothing to attest against).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.reputation_service import recompute_all_reputations
from app.services.web3 import web3_service

logger = logging.getLogger(__name__)


async def anchor_reputations() -> dict:
    """Recompute reputations and attest them on-chain.

    Returns counters for observability. Runs on the APScheduler and can be
    triggered manually via the admin router.
    """
    settings = get_settings()
    logger.info("Starting on-chain reputation anchoring job...")

    async with AsyncSessionLocal() as db:
        updated = await recompute_all_reputations(db)

        result = await db.execute(
            select(User).where(User.wallet_address.isnot(None))
        )
        users = list(result.scalars().all())

        attested = 0
        skipped = 0
        for user in users:
            score = float(user.reputation_score or 0)
            # Already synced to the same score — skip
            if user.onchain_score is not None and abs(user.onchain_score - score) < 0.005:
                skipped += 1
                continue

            score_scaled = int(round(score * 100))  # two decimals on-chain
            observed_at = int(datetime.now(timezone.utc).timestamp())

            try:
                tx_hash = web3_service.attest_reputation(
                    user.wallet_address, score_scaled, observed_at
                )
            except ValueError as e:
                # Configuration missing — no point trying the rest of the batch
                logger.error("Reputation anchoring not configured: %s", e)
                break
            except Exception as e:
                logger.warning("Attestation failed for %s: %s", user.handle, e)
                continue

            user.onchain_score = score
            user.onchain_tx_hash = tx_hash
            user.onchain_synced_at = datetime.now(timezone.utc)
            attested += 1

        await db.commit()
        logger.info(
            "Reputation anchoring done: %d recomputed, %d attested, %d up-to-date",
            updated, attested, skipped,
        )
        return {"users_recomputed": updated, "attested": attested, "up_to_date": skipped}
