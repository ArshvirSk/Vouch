"""Falsifiability check service — TRD §4.5.

MVP behavior: a deterministic heuristic pre-check (minimum length / numeric
content) runs first; when LLM checks are enabled and a Gemini API key is
configured, the shared LLMEngine (app.services.llm) performs the real check
with structured JSON output. When LLM checks are disabled the heuristic
verdict is returned directly, and failures fail open.
"""

import re

from app.schemas import FalsifiabilityResult
from app.services.llm import llm_engine

# A condition shorter than this is rarely meaningfully verifiable.
MIN_CONDITION_LENGTH = 10
# Reasonable conditions almost always contain a number (quantity, date, etc.).
_NUMBER_RE = re.compile(r"\d")


def check_falsifiability(measurable_condition: str) -> FalsifiabilityResult:
    """Check whether a commitment's measurable condition is falsifiable.

    Runs a cheap heuristic first; defers to the LLM engine when enabled.
    """
    condition = measurable_condition.strip()

    if len(condition) < MIN_CONDITION_LENGTH or not _NUMBER_RE.search(condition):
        return FalsifiabilityResult(
            is_falsifiable=False,
            reason=(
                "Condition is too vague to be meaningfully verifiable. "
                "Add specific numbers, dates, or measurable outcomes."
            ),
        )

    if not llm_engine.enabled or not llm_engine.client:
        return FalsifiabilityResult(
            is_falsifiable=True,
            reason="Heuristic check passed (LLM check disabled).",
        )

    return llm_engine.check_falsifiability(condition)
