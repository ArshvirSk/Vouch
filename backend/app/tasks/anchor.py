import logging
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.models.commitment import Commitment
from app.services.web3 import web3_service

logger = logging.getLogger(__name__)

# Leaves of each anchored batch are persisted here so Merkle proofs can be
# generated later. Written by anchor_pending_commitments(). Resolved relative
# to this file so it works regardless of the process working directory.
ANCHOR_LOG_PATH = Path(__file__).resolve().parents[2] / "scratch" / "anchor_log.json"


def _build_merkle_root(leaves: list[str]) -> str:
    """Build a real Merkle root from leaf hashes (sha256, binary tree).

    Leaf count is padded up to the next power of two by duplicating the
    last leaf (standard Bitcoin-style padding) so the tree is always
    balanced and proofs are unambiguous.
    """
    if not leaves:
        raise ValueError("Cannot build a Merkle root with no leaves")

    level = [bytes.fromhex(leaf) for leaf in leaves]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [
            hashlib.sha256(level[i] + level[i + 1]).digest()
            for i in range(0, len(level), 2)
        ]
    return level[0].hex()


def _append_anchor_log(commitments: list[Commitment], batch_root: str, tx_hash: str) -> None:
    """Persist the leaves of an anchored batch so proofs can be built later."""
    entry = {
        "batch_root": batch_root,
        "tx_hash": tx_hash,
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "leaves": [
            {"commitment_id": str(c.id), "content_hash": c.content_hash}
            for c in commitments
        ],
    }
    try:
        ANCHOR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(ANCHOR_LOG_PATH, "r", encoding="utf-8") as f:
                log = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            log = []
        log.append(entry)
        with open(ANCHOR_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2)
    except OSError as e:
        # Never fail the anchoring job because of log persistence
        logger.warning("Could not persist anchor log: %s", e)


async def anchor_pending_commitments():
    """
    Finds all commitments that have a content_hash but no onchain_tx_hash,
    computes a real Merkle root over their content hashes, anchors it to
    Polygon, and updates the onchain_tx_hash for those commitments.
    """
    logger.info("Starting batch anchoring job...")

    async with AsyncSessionLocal() as db:
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

        # Defensive: leaves must be 32-byte hex. A single malformed row must
        # not crash the whole batch — skip it with a warning instead.
        valid_commitments = []
        for c in commitments:
            h = (c.content_hash or "").strip().lower()
            if len(h) != 64:
                logger.warning(
                    "Skipping commitment %s: content_hash is not a 64-char hex string", c.id
                )
                continue
            try:
                bytes.fromhex(h)
            except ValueError:
                logger.warning("Skipping commitment %s: content_hash is not valid hex", c.id)
                continue
            valid_commitments.append(c)

        if not valid_commitments:
            logger.warning("All candidate commitments had malformed content hashes; nothing anchored.")
            return
        commitments = valid_commitments

        # Real Merkle root: leaves are the commitment content hashes, paired
        # and hashed up a binary tree (with last-leaf padding). Leaves are
        # persisted to the anchor log so proofs can be generated later.
        leaves = [c.content_hash for c in commitments]
        batch_root = _build_merkle_root(leaves)
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

            # Persist the batch leaves alongside the root + tx hash so that
            # Merkle inclusion proofs can be reconstructed later.
            _append_anchor_log(commitments, batch_root, tx_hash)

            logger.info(f"Successfully anchored {len(commitments)} commitments in tx {tx_hash}")
        except Exception as e:
            logger.error(f"Failed to anchor batch: {e}")
