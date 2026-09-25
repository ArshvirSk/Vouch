import logging

from google import genai
from pydantic import BaseModel, Field

from app.config import get_settings
from app.schemas import FalsifiabilityResult

settings = get_settings()

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Phase 4: structured output schemas
# ──────────────────────────────────────────────

class ExtractedCommitmentDraft(BaseModel):
    """One candidate promise extracted from a public statement."""
    subject_name: str = Field(description="Name of the person or organization making the promise.")
    statement: str = Field(description="The promise exactly as stated in the source text.")
    reformulated_condition: str = Field(
        description="The promise rewritten as a specific, measurable, falsifiable condition a jury could verify."
    )
    suggested_deadline: str | None = Field(
        None,
        description="Deadline if one is stated in the text, as an ISO date (YYYY-MM-DD). Null if none is stated.",
    )
    confidence: float = Field(description="0.0-1.0 confidence that this is a genuine, concrete promise.")


class ExtractionListResult(BaseModel):
    commitments: list[ExtractedCommitmentDraft] = Field(description="All concrete promises found in the text. Empty list if none.")


class ContradictionDraft(BaseModel):
    """One detected conflict between a new statement and an existing commitment."""
    commitment_index: int = Field(description="Zero-based index of the existing commitment in the provided list.")
    explanation: str = Field(description="Short explanation of how the new statement conflicts with the commitment.")
    confidence: float = Field(description="0.0-1.0 confidence that this is a genuine contradiction.")


class ContradictionListResult(BaseModel):
    contradictions: list[ContradictionDraft] = Field(description="All conflicts found. Empty list if none.")


class LLMEngine:
    """Gemini-backed accountability engine with structured JSON output.

    All structured-output models double as return types, so every caller sees
    the same fields. The engine covers:
    - falsifiability checks (Phase 2)
    - NLP extraction of commitments from public statements (Phase 4)
    - contradiction detection against an existing commitment ledger (Phase 4)
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

    # ── Phase 2: falsifiability ──────────────────────────────

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

    # ── Phase 4: NLP extraction ──────────────────────────────

    def extract_commitments(self, text: str) -> ExtractionListResult:
        """Extract concrete promises from a public statement (news, transcript,
        speech, social post).

        Returns an ExtractionListResult — possibly empty when no concrete
        promises are found. Raises LLMDisabledError if the engine is off.
        """
        if not self.enabled or not self.client:
            raise LLMDisabledError()

        prompt = (
            "You are an analyst for a public accountability platform. Extract every concrete, "
            "falsifiable promise made in the following public statement. Only include statements "
            "where the speaker commits to a specific action, target, or outcome — ignore opinions, "
            "aspirations without specifics, and descriptions of past events. For each promise, "
            "reformulate it as a specific measurable condition that a jury could later verify as "
            "met or broken. Return an empty list if there are no concrete promises.\n\n"
            f"Statement: '''{text}'''"
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ExtractionListResult,
            },
        )
        return response.parsed or ExtractionListResult(commitments=[])

    # ── Phase 4: contradiction detection ─────────────────────

    def find_contradictions(
        self,
        new_statement: str,
        existing_commitments: list[dict[str, str]],
    ) -> ContradictionListResult:
        """Compare a new public statement against an existing ledger of
        commitments and flag conflicts.

        `existing_commitments` is a list of dicts with keys "title" and
        "condition" (order matters — indexes are returned in the result).
        Raises LLMDisabledError if the engine is off.
        """
        if not self.enabled or not self.client:
            raise LLMDisabledError()

        if not existing_commitments:
            return ContradictionListResult(contradictions=[])

        ledger_lines = "\n".join(
            f"[{i}] {c.get('title', '')}: {c.get('condition', '')}"
            for i, c in enumerate(existing_commitments)
        )

        prompt = (
            "You are a fact-consistency analyst for a public accountability platform. "
            "A public figure has made a new statement. Compare it against their existing ledger "
            "of tracked commitments below. Flag every case where the new statement conflicts with "
            "a commitment — e.g. abandoning, reversing, or contradicting a previously made promise. "
            "Do NOT flag cases that merely restate or reinforce a commitment. "
            "Return the index of each conflicting commitment with a short explanation. "
            "Return an empty list if there are no conflicts.\n\n"
            f"Existing commitments:\n{ledger_lines}\n\n"
            f"New statement: '''{new_statement}'''"
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ContradictionListResult,
            },
        )
        return response.parsed or ContradictionListResult(contradictions=[])


class LLMDisabledError(RuntimeError):
    """Raised when an LLM feature is used while the engine is not configured."""


llm_engine = LLMEngine()
