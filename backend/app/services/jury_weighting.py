"""Jury weighting math — Phase 4: reputation-weighted open juries.

Pure functions so the weighting policy is unit-testable in isolation from
the database task that uses it.
"""

import math
import random


def reputation_bonus(reputation_score: float) -> float:
    """Squash an unbounded reputation into a bounded jury-draw bonus.

    sqrt keeps order (higher reputation → higher bonus) but prevents whales
    from fully dominating; negative reputation contributes nothing.
    """
    if reputation_score <= 0:
        return 0.0
    return math.sqrt(reputation_score)


def juror_weight(stake: float, reputation_score: float) -> float:
    """Total draw weight for a pool candidate: stake + squashed reputation,
    floored at 1.0 so every member keeps a nonzero chance."""
    return max(1.0, stake + reputation_bonus(reputation_score))


def weighted_pick_without_replacement(candidates: list, weights: list[float], k: int) -> list:
    """Draw k distinct entries with odds proportional to their weights.

    Mirrors the sequential weighted draw used by the jury selection task.
    """
    if k <= 0 or not candidates:
        return []
    pool = list(zip(candidates, weights))
    picked = []
    for _ in range(min(k, len(pool))):
        entries = [e for e, _ in pool]
        w = [max(1.0, float(weight)) for _, weight in pool]
        chosen = random.choices(entries, weights=w, k=1)[0]
        picked.append(chosen)
        idx = entries.index(chosen)
        pool.pop(idx)
    return picked
