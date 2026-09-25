"""Milestone DB-layer integration tests (SQLite, no Postgres required).

Exercises the milestone router functions and the check_milestones service
against a real (SQLite) database so the full flow is validated even in
environments without a reachable Postgres instance.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DB_TESTS") == "1", reason="DB tests disabled"
)

from app.database import Base
from sqlalchemy.dialects.postgresql import JSONB

# --- SQLite compatibility patches (test-only) -------------------------------
# 1. JSONB has no SQLite rendering; treat it as generic JSON
JSONB.cache_ok = True


@pytest.fixture(scope="session", autouse=True)
def _sqlite_compat():
    from sqlalchemy import JSON, DefaultClause, text as sa_text

    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()
            if col.server_default is not None:
                default_sql = str(col.server_default.arg)
                if "gen_random_uuid" in default_sql:
                    col.server_default = None
                elif default_sql == "now()":
                    # SQLite has no now(); CURRENT_TIMESTAMP is the equivalent
                    col.server_default = DefaultClause(sa_text("CURRENT_TIMESTAMP"))
    yield


from app.models.user import User
from app.models.commitment import Commitment, CommitmentJuror, CommitmentStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.notification import Notification, NotificationType
from app.services.milestone_service import check_milestones
from app.routers import milestones as ms_router


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded(db):
    """Author + juror + a live public commitment."""
    author = User(handle=f"a{uuid.uuid4().hex[:8]}", email=f"a{uuid.uuid4().hex[:6]}@t.dev")
    juror = User(handle=f"j{uuid.uuid4().hex[:8]}", email=f"j{uuid.uuid4().hex[:6]}@t.dev")
    moderator = User(handle=f"m{uuid.uuid4().hex[:8]}", email=f"m{uuid.uuid4().hex[:6]}@t.dev", is_moderator=True)
    db.add_all([author, juror, moderator])
    await db.flush()

    commitment = Commitment(
        author_id=author.id,
        title="Ship v1 of the app",
        measurable_condition="Ship 3 features by the deadline, verified on the board",
        deadline=datetime.now(timezone.utc) + timedelta(days=30),
        content_hash="hash",
        is_public=True,
        jury_pool_size=3,
    )
    db.add(commitment)
    await db.flush()
    db.add(CommitmentJuror(commitment_id=commitment.id, juror_id=juror.id))
    await db.commit()
    return {"author": author, "juror": juror, "moderator": moderator, "commitment": commitment}


class FakePrincipal:
    def __init__(self, user: User):
        self.id = user.id
        self.handle = user.handle
        self.is_moderator = user.is_moderator


class TestMilestoneFlow:
    @pytest.mark.asyncio
    async def test_create_submit_verify_progress(self, db, seeded):
        d = seeded
        commitment = d["commitment"]

        # Author creates two milestones
        await ms_router.create_milestone(
            commitment.id,
            ms_router.MilestoneCreate(title="Design doc", progress_weight=1.0),
            db=db,
            current_user=FakePrincipal(d["author"]),
        )
        await ms_router.create_milestone(
            commitment.id,
            ms_router.MilestoneCreate(title="Public beta", progress_weight=3.0),
            db=db,
            current_user=FakePrincipal(d["author"]),
        )

        listing = await ms_router.list_milestones(commitment.id, db=db)
        assert listing.total_count == 2
        assert listing.progress == 0.0

        # Author submits the first; juror verifies it
        result = await db.execute(select(Milestone).where(Milestone.title == "Design doc"))
        m1 = result.scalar_one()
        submitted = await ms_router.submit_milestone(commitment.id, m1.id, db=db, current_user=FakePrincipal(d["author"]))
        assert submitted.status == "submitted"

        verified = await ms_router.verify_milestone(
            commitment.id, m1.id,
            ms_router.MilestoneStatusUpdate(decision="verified"),
            db=db, current_user=FakePrincipal(d["juror"]),
        )
        assert verified.status == "verified"
        assert verified.verified_at is not None

        # Weighted progress: 1/(1+3) = 0.25
        listing = await ms_router.list_milestones(commitment.id, db=db)
        assert listing.progress == pytest.approx(0.25)
        assert listing.verified_count == 1

    @pytest.mark.asyncio
    async def test_author_cannot_verify_own_milestone(self, db, seeded):
        d = seeded
        await ms_router.create_milestone(
            d["commitment"].id,
            ms_router.MilestoneCreate(title="Design doc"),
            db=db, current_user=FakePrincipal(d["author"]),
        )
        m = (await db.execute(select(Milestone))).scalar_one()
        await ms_router.submit_milestone(d["commitment"].id, m.id, db=db, current_user=FakePrincipal(d["author"]))

        with pytest.raises(HTTPException) as exc_info:
            await ms_router.verify_milestone(
                d["commitment"].id, m.id,
                ms_router.MilestoneStatusUpdate(decision="verified"),
                db=db, current_user=FakePrincipal(d["author"]),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_non_juror_cannot_verify(self, db, seeded):
        d = seeded
        outsider = User(handle=f"o{uuid.uuid4().hex[:8]}", email=f"o{uuid.uuid4().hex[:6]}@t.dev")
        db.add(outsider)
        await db.commit()

        await ms_router.create_milestone(
            d["commitment"].id,
            ms_router.MilestoneCreate(title="Design doc"),
            db=db, current_user=FakePrincipal(d["author"]),
        )
        m = (await db.execute(select(Milestone))).scalar_one()
        await ms_router.submit_milestone(d["commitment"].id, m.id, db=db, current_user=FakePrincipal(d["author"]))

        with pytest.raises(HTTPException) as exc_info:
            await ms_router.verify_milestone(
                d["commitment"].id, m.id,
                ms_router.MilestoneStatusUpdate(decision="verified"),
                db=db, current_user=FakePrincipal(outsider),
            )
        assert exc_info.value.status_code == 403

        # ...but the assigned juror can
        result = await ms_router.verify_milestone(
            d["commitment"].id, m.id,
            ms_router.MilestoneStatusUpdate(decision="verified"),
            db=db, current_user=FakePrincipal(d["juror"]),
        )
        assert result.status == "verified"

    @pytest.mark.asyncio
    async def test_moderator_can_verify(self, db, seeded):
        d = seeded
        await ms_router.create_milestone(
            d["commitment"].id,
            ms_router.MilestoneCreate(title="Design doc"),
            db=db, current_user=FakePrincipal(d["author"]),
        )
        m = (await db.execute(select(Milestone))).scalar_one()
        await ms_router.submit_milestone(d["commitment"].id, m.id, db=db, current_user=FakePrincipal(d["author"]))

        result = await ms_router.verify_milestone(
            d["commitment"].id, m.id,
            ms_router.MilestoneStatusUpdate(decision="verified"),
            db=db, current_user=FakePrincipal(d["moderator"]),
        )
        assert result.status == "verified"


class TestMilestoneServicePass:
    @pytest.mark.asyncio
    async def test_due_soon_and_missed(self, db, seeded):
        d = seeded
        now = datetime.now(timezone.utc)
        ms = [
            Milestone(commitment_id=d["commitment"].id, title="due soon", position=0,
                      progress_weight=1.0, target_date=now + timedelta(hours=24),
                      status=MilestoneStatus.PENDING),
            Milestone(commitment_id=d["commitment"].id, title="already late", position=1,
                      progress_weight=1.0, target_date=now - timedelta(days=1),
                      status=MilestoneStatus.PENDING),
            Milestone(commitment_id=d["commitment"].id, title="far away", position=2,
                      progress_weight=1.0, target_date=now + timedelta(days=10),
                      status=MilestoneStatus.PENDING),
        ]
        db.add_all(ms)
        await db.commit()

        result = await check_milestones(db)
        assert result["reminders_sent"] == 1   # only 'due soon'
        assert result["milestones_missed"] == 1  # only 'already late'

        statuses = {m.title: m.status for m in (await db.execute(select(Milestone))).scalars()}
        assert statuses["already late"] == MilestoneStatus.MISSED
        assert statuses["due soon"] == MilestoneStatus.PENDING
        assert statuses["far away"] == MilestoneStatus.PENDING

        # Author got a MILESTONE_DUE notification
        notes = (await db.execute(
            select(Notification).where(Notification.type == NotificationType.MILESTONE_DUE)
        )).scalars().all()
        assert len(notes) == 2  # reminder + missed notice
