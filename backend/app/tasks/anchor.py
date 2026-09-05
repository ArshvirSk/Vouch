import logging
import hashlib
from app.db.session import get_db_context
from app.models.commitment import Commitment
from app.services.web3 import web3_service
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

async def anchor_pending_commitments():
    """
    Finds all commitments that have a content_hash but no onchain_tx_hash,
    computes a simple Merkle-like batch root, anchors it to Polygon, 
    and updates the onchain_tx_hash for those commitments.
    """
    logger.info("Starting batch anchoring job...")
    
    async with get_db_context() as db:
        # Get commitments to anchor
        stmt = select(Commitment).where(
            Commitment.content_hash.isnot(None),
            Commitment.onchain_tx_hash.is_(None)
        ).order_by(Commitment.created_at.asc())
        
        result = await db.execute(stmt)
        commitments = result.scalars().all()
        
        if not commitments:
            logger.info("No new commitments to anchor.")
            return
            
        logger.info(f"Found {len(commitments)} commitments to anchor.")
        
        # Extremely simplified "Merkle Root" for the batch (just hashing all hashes together)
        # In production, we'd use a real Merkle tree library and save the leaves
        batch_hasher = hashlib.sha256()
        for c in commitments:
            batch_hasher.update(c.content_hash.encode('utf-8'))
            
        batch_root = batch_hasher.hexdigest()
        logger.info(f"Computed batch root: {batch_root}")
        
        try:
            # Anchor to blockchain
            tx_hash = web3_service.anchor_merkle_root(batch_root)
            
            # Update DB
            commitment_ids = [c.id for c in commitments]
            update_stmt = (
                update(Commitment)
                .where(Commitment.id.in_(commitment_ids))
                .values(onchain_tx_hash=tx_hash)
            )
            await db.execute(update_stmt)
            await db.commit()
            
            logger.info(f"Successfully anchored {len(commitments)} commitments in tx {tx_hash}")
        except Exception as e:
            logger.error(f"Failed to anchor batch: {e}")
