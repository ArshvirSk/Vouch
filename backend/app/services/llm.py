import logging

from google import genai

from app.config import get_settings
from app.schemas import FalsifiabilityResult

settings = get_settings()

logger = logging.getLogger(__name__)


class LLMEngine:
    """Gemini-backed falsifiability engine with structured JSON output.

    Uses the shared FalsifiabilityResult schema (app.schemas) both as the
    Gemini response_schema and as the return type, so every caller sees the
    same fields (is_falsifiable / reason / suggested_rewrite).
    """

    def __init__(self):
        self.enabled = settings.enable_llm_check
        self.api_key = settings.gemini_api_key
        self.model = settings.llm_model

        if self.enabled and self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            if self.enabled:
                logger.warning("LLM Check enabled but GEMINI_API_KEY is missing.")

    def check_falsifiability(self, text: str) -> FalsifiabilityResult:
        """
        Uses Gemini to evaluate if a commitment is falsifiable.
        Returns a heuristic-neutral result if LLM checks are disabled.
        """
        if not self.enabled or not self.client:
            return FalsifiabilityResult(
                is_falsifiable=True,
                reason="LLM check disabled.",
                suggested_rewrite=None,
            )

        try:
            prompt = (
                "You are an expert moderator for a public accountability platform. "
                "Analyze the following commitment text and determine if it is falsifiable. "
                "A statement is falsifiable if it has a clear, objective condition that can be proven true or false. "
                "Vague promises like 'I will improve the economy' are NOT falsifiable. "
                "Specific promises like 'I will pass Bill XYZ by March 1st' are falsifiable.\n\n"
                f"Commitment: '{text}'"
            )

            # Use Structured Outputs with Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": FalsifiabilityResult,
                },
            )

            return response.parsed

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            # Fail open if the LLM is down so users aren't blocked
            return FalsifiabilityResult(
                is_falsifiable=True,
                reason="LLM service error, defaulting to true.",
                suggested_rewrite=None,
            )


llm_engine = LLMEngine()
