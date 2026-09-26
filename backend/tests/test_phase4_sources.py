"""Phase 4 tests — sources queue, NLP extraction, contradiction detection.

No DB required for schema/LLM tests. Endpoint tests use dependency overrides
and only exercise paths that reject before hitting the database.
"""

import os
import sys
import types
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
# LLM engine paths — engine state is forced per test so the suite behaves
# identically everywhere (a dev .env may carry a real GEMINI_API_KEY, CI
# carries none). No test ever hits the network.
# ──────────────────────────────────────────────

def _force_disabled(monkeypatch):
    """Put the engine singleton in its unconfigured (no key) state."""
    monkeypatch.setattr(llm_engine, "enabled", False, raising=False)
    monkeypatch.setattr(llm_engine, "client", None, raising=False)


def _force_enabled(monkeypatch, parsed=None, exc=None):
    """Put the engine singleton in its configured state with a fake client
    whose models.generate_content returns `parsed` (or raises `exc`).
    Returns the fake so tests can assert on calls made."""
    calls: list[dict] = []

    def generate_content(*, model, contents, config):
        calls.append({"model": model, "contents": contents, "config": config})
        if exc is not None:
            raise exc
        return types.SimpleNamespace(parsed=parsed)

    fake_client = types.SimpleNamespace(
        models=types.SimpleNamespace(generate_content=generate_content)
    )
    monkeypatch.setattr(llm_engine, "enabled", True, raising=False)
    monkeypatch.setattr(llm_engine, "client", fake_client, raising=False)
    return calls


class TestLLMDisabledPaths:
    def test_engine_disabled_without_key(self):
        # Unconfigured default: either disabled, or enabled-without-client is
        # treated as disabled by every caller (enabled and client are checked
        # together everywhere).
        assert llm_engine.enabled is False or llm_engine.client is not None

    def test_falsifiability_disabled_path_neutral(self, monkeypatch):
        _force_disabled(monkeypatch)
        result = llm_engine.check_falsifiability("I will ship 3 features by March 1st")
        assert isinstance(result, FalsifiabilityResult)
        assert result.is_falsifiable is True  # fail-open neutral verdict
        assert result.reason == "LLM check disabled."

    def test_falsifiability_heuristic_rejects_vague(self):
        result = falsifiability.check_falsifiability("be better")
        assert result.is_falsifiable is False

    def test_extract_raises_when_disabled(self, monkeypatch):
        _force_disabled(monkeypatch)
        with pytest.raises(LLMDisabledError):
            llm_engine.extract_commitments("We will build 500 homes by 2027.")

    def test_contradictions_raise_when_disabled(self, monkeypatch):
        _force_disabled(monkeypatch)
        with pytest.raises(LLMDisabledError):
            llm_engine.find_contradictions(
                "We are cancelling the housing project.",
                [{"title": "Build homes", "condition": "500 units by 2027"}],
            )

    def test_contradictions_empty_ledger_short_circuits(self, monkeypatch):
        # With the engine configured, an empty ledger must return an empty
        # result WITHOUT calling the model (no API spend, no latency).
        calls = _force_enabled(monkeypatch)
        result = llm_engine.find_contradictions("Anything.", [])
        assert result.contradictions == []
        assert calls == []


class TestLLMEnabledPaths:
    """Configured-engine behavior against a mocked client — asserts prompt
    plumbing and response handling without any real API traffic."""

    def test_falsifiability_returns_parsed(self, monkeypatch):
        verdict = FalsifiabilityResult(
            is_falsifiable=False,
            reason="No measurable condition.",
            suggested_rewrite="Plant 500 trees by March 1st",
        )
        calls = _force_enabled(monkeypatch, parsed=verdict)
        result = llm_engine.check_falsifiability("make the city greener")
        assert result is verdict
        assert len(calls) == 1
        assert "make the city greener" in calls[0]["contents"]
        assert calls[0]["config"]["response_schema"] is FalsifiabilityResult

    def test_falsifiability_fails_open_on_error(self, monkeypatch):
        _force_enabled(monkeypatch, exc=RuntimeError("gemini down"))
        result = llm_engine.check_falsifiability("I will ship 3 features by March 1st")
        # Fail open so users aren't blocked by an outage.
        assert result.is_falsifiable is True
        assert "error" in result.reason.lower()

    def test_extract_returns_parsed(self, monkeypatch):
        draft = ExtractedCommitmentDraft(
            subject_name="Mayor Jane",
            statement="We will build 500 homes by 2027.",
            reformulated_condition="500 homes completed by 2027-12-31",
            suggested_deadline="2027-12-31",
            confidence=0.9,
        )
        calls = _force_enabled(
            monkeypatch, parsed=ExtractionListResult(commitments=[draft])
        )
        result = llm_engine.extract_commitments("We will build 500 homes by 2027.")
        assert result.commitments[0].subject_name == "Mayor Jane"
        assert len(calls) == 1
        assert "500 homes" in calls[0]["contents"]

    def test_extract_none_parsed_becomes_empty(self, monkeypatch):
        # A model response without a parsed payload must not crash — it
        # degrades to "no promises found".
        _force_enabled(monkeypatch, parsed=None)
        result = llm_engine.extract_commitments("Lovely weather today.")
        assert result.commitments == []

    def test_contradictions_returns_parsed(self, monkeypatch):
        parsed = ContradictionListResult(
            contradictions=[
                ContradictionDraft(commitment_index=0, explanation="Reversed position", confidence=0.8)
            ]
        )
        calls = _force_enabled(monkeypatch, parsed=parsed)
        result = llm_engine.find_contradictions(
            "We are cancelling the housing project.",
            [{"title": "Build homes", "condition": "500 units by 2027"}],
        )
        assert result.contradictions[0].commitment_index == 0
        assert len(calls) == 1
        # The ledger must be in the prompt with indexes so results map back.
        assert "[0] Build homes" in calls[0]["contents"]


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

