"""Falsifiability check service — TRD §4.5.

MVP: stubbed mock that always returns is_falsifiable=True.
Production: replace with real LLM call (Anthropic/OpenAI).
"""

from app.schemas import FalsifiabilityResult


async def check_falsifiability(measurable_condition: str) -> FalsifiabilityResult:
    """Check whether a commitment's measurable condition is falsifiable.

    MVP stub: always returns True. In production, this makes a single LLM call
    with structured JSON output {is_falsifiable: bool, reason: string}.

    TODO: Wire real LLM API (Anthropic Claude or OpenAI GPT-4) when
    VOUCH_LLM_ENABLED=true. Cache nothing — this is cheap and infrequent (TRD §4.5).
    """
    # Minimal sanity check even in stub mode
    if len(measurable_condition.strip()) < 10:
        return FalsifiabilityResult(
            is_falsifiable=False,
            reason="Condition is too short to be meaningfully verifiable. Add specific numbers, dates, or measurable outcomes.",
        )

    return FalsifiabilityResult(
        is_falsifiable=True,
        reason="Mocked — real LLM falsifiability check not wired. "
               "In production, this will validate that the condition is specific, "
               "measurable, and verifiable by a third party.",
    )
