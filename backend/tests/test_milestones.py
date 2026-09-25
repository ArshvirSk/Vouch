"""Milestone tracking tests — progress math + router validation paths."""

import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.milestone import Milestone, MilestoneStatus
from app.services.milestone_service import compute_progress


def _m(status="pending", weight=1.0):
    return Milestone(
        id=uuid.uuid4(),
        commitment_id=uuid.uuid4(),
        title="m",
        detail=None,
        position=0,
        progress_weight=weight,
        target_date=None,
        status=MilestoneStatus(status),
        verified_by_id=None,
        verified_at=None,
    )


class TestComputeProgress:
    def test_no_milestones(self):
        assert compute_progress([]) == 0.0

    def test_all_verified_is_full(self):
        ms = [_m("verified"), _m("verified"), _m("verified")]
        assert compute_progress(ms) == pytest.approx(1.0)

    def test_half_verified_half_pending(self):
        ms = [_m("verified"), _m("pending")]
        assert compute_progress(ms) == pytest.approx(0.5)

    def test_weights_are_respected(self):
        ms = [_m("verified", weight=3.0), _m("pending", weight=1.0)]
        assert compute_progress(ms) == pytest.approx(0.75)

    def test_missed_counts_as_zero(self):
        ms = [_m("verified"), _m("missed")]
        assert compute_progress(ms) == pytest.approx(0.5)

    def test_submitted_is_not_progress_until_verified(self):
        ms = [_m("submitted"), _m("submitted")]
        assert compute_progress(ms) == 0.0

    def test_zero_total_weight_is_safe(self):
        assert compute_progress([_m("pending", weight=0.0)]) == 0.0


class TestMilestoneSchemas:
    def test_status_enum_values(self):
        assert MilestoneStatus.PENDING.value == "pending"
        assert MilestoneStatus.SUBMITTED.value == "submitted"
        assert MilestoneStatus.VERIFIED.value == "verified"
        assert MilestoneStatus.MISSED.value == "missed"

    def test_create_validation_rejects_bad_weight(self):
        from app.routers.milestones import MilestoneCreate

        with pytest.raises(ValueError):
            MilestoneCreate(title="Valid title", progress_weight=0)

    def test_create_validation_rejects_short_title(self):
        from app.routers.milestones import MilestoneCreate

        with pytest.raises(ValueError):
            MilestoneCreate(title="ab")

    def test_status_update_rejects_bad_decision(self):
        from app.routers.milestones import MilestoneStatusUpdate

        with pytest.raises(ValueError):
            MilestoneStatusUpdate(decision="maybe")


class TestMilestoneGuards:
    @pytest.mark.asyncio
    async def test_non_author_cannot_submit(self):
        from app.routers.milestones import _require_author_or_moderator

        class FakeUser:
            id = uuid.uuid4()
            is_moderator = False

        class FakeCommitment:
            author_id = uuid.uuid4()  # different user

        with pytest.raises(HTTPException) as exc_info:
            await _require_author_or_moderator(FakeCommitment(), FakeUser())
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_moderator_can_manage(self):
        from app.routers.milestones import _require_author_or_moderator

        class FakeUser:
            id = uuid.uuid4()
            is_moderator = True

        class FakeCommitment:
            author_id = uuid.uuid4()

        await _require_author_or_moderator(FakeCommitment(), FakeUser())  # no raise

    @pytest.mark.asyncio
    async def test_author_can_manage(self):
        from app.routers.milestones import _require_author_or_moderator

        user_id = uuid.uuid4()

        class FakeUser:
            id = user_id
            is_moderator = False

        class FakeCommitment:
            author_id = user_id

        await _require_author_or_moderator(FakeCommitment(), FakeUser())  # no raise
