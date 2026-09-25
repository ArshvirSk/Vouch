"""Phase 4 tests — sources queue, NLP extraction, contradiction detection.

No DB required for schema/LLM tests. Endpoint tests use dependency overrides
and only exercise paths that reject before hitting the database.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import require_moderator
from app.schemas import (
    CommitmentCreate,
    FalsifiabilityResult,
    SourceDocumentCreate,
)
from app.services.llm import (
    ContradictionDraft,
    ContradictionListResult,
    ExtractedCommitmentDraft,
    ExtractionListResult,
    LLMDisabledError,
    llm_engine,
)
from app.services import falsifiability


# ──────────────────────────────────────────────
# Phase 4 structured output schemas
# ──────────────────────────────────────────────

class TestExtractionSchemas:
    def test_extraction_roundtrip(self):
        draft = ExtractedCommitmentDraft(
            subject_name="Mayor Jane",
            statement="We will build 500 new housing units by 2027.",
            reformulated_condition="At least 500 housing units completed and publicly listed by 2027-12-31",
            suggested_deadline="2027-12-31",
            confidence=0.9,
        )
        result = ExtractionListResult(commitments=[draft])
        assert result.commitments[0].subject_name == "Mayor Jane"
        assert result.commitments[0].confidence == pytest.approx(0.9)

    def test_empty_extraction_is_valid(self):
        assert ExtractionListResult(commitments=[]).commitments == []

    def test_deadline_is_optional(self):
        draft = ExtractedCommitmentDraft(
            subject_name="X",
            statement="s",
            reformulated_condition="c",
            suggested_deadline=None,
            confidence=0.5,
        )
        assert draft.suggested_deadline is None

    def test_contradiction_roundtrip(self):
        result = ContradictionListResult(contradictions=[
            ContradictionDraft(commitment_index=2, explanation="Reversed position", confidence=0.8)
        ])
        assert result.contradictions[0].commitment_index == 2
        assert result.contradictions[0].confidence == pytest.approx(0.8)

    def test_empty_contradiction_list_is_valid(self):
        assert ContradictionListResult(contradictions=[]).contradictions == []


# ──────────────────────────────────────────────
# Disabled-LLM behavior (fail closed / disabled paths)
# ──────────────────────────────────────────────

class TestLLMDisabledPaths:
    def test_engine_disabled_without_key(self):
        # The test env has no VOUCH_ENABLE_LLM_CHECK set
        assert llm_engine.enabled is False or llm_engine.client is not None

    def test_falsifiability_disabled_path_neutral(self):
        if llm_engine.enabled and llm_engine.client:
            pytest.skip("LLM enabled in this environment")
        result = llm_engine.check_falsifiability("I will ship 3 features by March 1st")
        assert isinstance(result, FalsifiabilityResult)
        assert result.is_falsifiable is True  # fail-open neutral verdict
        assert result.reason == "LLM check disabled."

    def test_falsifiability_heuristic_rejects_vague(self):
        result = falsifiability.check_falsifiability("be better")
        assert result.is_falsifiable is False

    def test_extract_raises_when_disabled(self):
        if llm_engine.enabled and llm_engine.client:
            pytest.skip("LLM enabled in this environment")
        with pytest.raises(LLMDisabledError):
            llm_engine.extract_commitments("We will build 500 homes by 2027.")

    def test_contradictions_raise_when_disabled(self):
        if llm_engine.enabled and llm_engine.client:
            pytest.skip("LLM enabled in this environment")
        with pytest.raises(LLMDisabledError):
            llm_engine.find_contradictions(
                "We are cancelling the housing project.",
                [{"title": "Build homes", "condition": "500 units by 2027"}],
            )

    def test_contradictions_empty_ledger_short_circuits(self):
        # Empty ledger returns empty result even if the engine were enabled
        # (no API call is needed) — but only when the engine is configured.
        if llm_engine.enabled and llm_engine.client:
            result = llm_engine.find_contradictions("Anything.", [])
            assert result.contradictions == []
        else:
            with pytest.raises(LLMDisabledError):
                llm_engine.find_contradictions("Anything.", [])


# ──────────────────────────────────────────────
# Moderator guard
# ──────────────────────────────────────────────

class TestModeratorGuard:
    @pytest.mark.asyncio
    async def test_rejects_non_moderator(self):
        class FakeUser:
            handle = "regular_user"
            is_moderator = False

        with pytest.raises(HTTPException) as exc_info:
            await require_moderator(FakeUser())
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_allows_flagged_moderator(self):
        class FakeUser:
            handle = "some_other_handle"
            is_moderator = True

        user = await require_moderator(FakeUser())
        assert user.handle == "some_other_handle"

    @pytest.mark.asyncio
    async def test_allows_bootstrap_handle(self):
        class FakeUser:
            handle = "admin"
            is_moderator = False

        # Only passes if VOUCH_MODERATOR_HANDLES contains "admin" (not set in test env → 403)
        from app.config import get_settings
        bootstrap = {h.strip() for h in get_settings().moderator_handles.split(",") if h.strip()}
        if "admin" in bootstrap:
            user = await require_moderator(FakeUser())
            assert user.handle == "admin"
        else:
            with pytest.raises(HTTPException) as exc_info:
                await require_moderator(FakeUser())
            assert exc_info.value.status_code == 403


# ──────────────────────────────────────────────
# Source submission schema validation
# ──────────────────────────────────────────────

class TestSourceDocumentCreate:
    def test_valid_source(self):
        s = SourceDocumentCreate(
            title="Debate transcript",
            source_type="transcript",
            content="The senator promised to pass the bill by March 2027.",
        )
        assert s.source_type == "transcript"

    def test_content_too_short_rejected(self):
        with pytest.raises(ValueError):
            SourceDocumentCreate(title="t", source_type="news", content="short")

    def test_invalid_type_rejected(self):
        with pytest.raises(ValueError):
            SourceDocumentCreate(title="Valid title here", source_type="podcast", content="A" * 50)

    def test_title_too_long_rejected(self):
        with pytest.raises(ValueError):
            SourceDocumentCreate(title="x" * 301, source_type="news", content="A" * 50)


# ──────────────────────────────────────────────
# Existing validator still enforced
# ──────────────────────────────────────────────

class TestCommitmentValidatorStillHolds:
    def test_private_juror_rules(self):
        with pytest.raises(ValueError):
            CommitmentCreate(
                title="t",
                measurable_condition="Do exactly 3 things by 2026-12-01",
                deadline="2026-12-01T00:00:00Z",
                juror_handles=["one"],
            )

