"""Falsifiability check service — TRD §4.5.

MVP: stubbed mock that always returns is_falsifiable=True.
Production: replace with real LLM call (Anthropic/OpenAI).
"""

import json
import google.generativeai as genai
from app.schemas import FalsifiabilityResult
from app.config import get_settings

settings = get_settings()

if settings.llm_enabled and settings.llm_api_key:
    genai.configure(api_key=settings.llm_api_key)


async def check_falsifiability(measurable_condition: str) -> FalsifiabilityResult:
    """Check whether a commitment's measurable condition is falsifiable."""
    if not settings.llm_enabled or not settings.llm_api_key:
        if len(measurable_condition.strip()) < 10:
            return FalsifiabilityResult(
                is_falsifiable=False,
                reason="Condition is too short to be meaningfully verifiable. Add specific numbers, dates, or measurable outcomes.",
            )
        return FalsifiabilityResult(
            is_falsifiable=True,
            reason="Mocked — real LLM falsifiability check not wired.",
        )

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        You are a neutral judge. Evaluate if the following commitment condition is falsifiable (specific, measurable, and verifiable by a third party).
        Condition: "{measurable_condition}"
        Return ONLY valid JSON with two keys:
        - "is_falsifiable": boolean
        - "reason": string explaining why it is or isn't falsifiable
        """
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        data = json.loads(text)
        return FalsifiabilityResult(
            is_falsifiable=bool(data.get("is_falsifiable", False)),
            reason=str(data.get("reason", "Failed to parse reason from LLM."))
        )
    except Exception as e:
        # Fallback in case of API error
        return FalsifiabilityResult(
            is_falsifiable=True,
            reason=f"LLM check failed ({str(e)}). Proceeding by default."
        )
