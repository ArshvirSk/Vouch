"""Full-lifecycle smoke test against the live DB.

Runs one personal commitment through the real pipeline using the actual
router functions (no direct DB writes for the flow itself):

  create (falsifiability + juror validation)
    -> submit evidence (open -> evidence_submitted)
    -> deadline passes -> check_deadlines job (-> in_verification)
    -> cast votes as the invited jurors (auto-resolve on last vote)
    -> resolution -> reputation events -> reputation recompute job
    -> verify /users/{handle} stats updated (Part 1 step 2 fields)

Prints before/after values for every observed number and restores the DB
afterwards (the seeded Mumbai data stays; only this test's rows are removed).

Run: cd backend && python -m scripts.lifecycle_smoke
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.commitment import Commitment, CommitmentJuror
from app.models.evidence import Evidence
from app.models.vote import Vote
from app.models.reputation import ReputationEvent
from app.models.notification import Notification
from app.models.milestone import Milestone
from app.routers import commitments as c_router
from app.routers import evidence as e_router
from app.routers import users as u_router
from app.routers.votes import cast_vote
from app.jobs.deadline_checker import check_deadlines
from app.services.reputation_service import recompute_reputation
from app.schemas import CommitmentCreate, EvidenceCreate, VoteCreate


class Principal:
    def __init__(self, user: User):
        self.id = user.id
        self.handle = user.handle


def line(label, before, after):
    mark = "CHANGED" if before != after else "same"
    print(f"    {label:34s} {str(before):>8} -> {str(after):<8} [{mark}]")


async def cleanup(db):
    rows = (await db.execute(select(User).where(User.handle.like("smoke_lc_%")))).scalars().all()
    if not rows:
        return
    ids = [u.id for u in rows]
    commit_ids = (await db.execute(
        select(Commitment.id).where(Commitment.author_id.in_(ids))
    )).scalars().all()
    for stmt in (
        delete(Milestone).where(Milestone.commitment_id.in_(commit_ids)),
        delete(Vote).where(Vote.commitment_id.in_(commit_ids)),
        delete(Vote).where(Vote.juror_id.in_(ids)),
        delete(Evidence).where(Evidence.commitment_id.in_(commit_ids)),
        delete(Evidence).where(Evidence.submitter_id.in_(ids)),
        delete(CommitmentJuror).where(CommitmentJuror.commitment_id.in_(commit_ids)),
        delete(CommitmentJuror).where(CommitmentJuror.juror_id.in_(ids)),
        delete(Notification).where(Notification.user_id.in_(ids)),
        delete(ReputationEvent).where(ReputationEvent.commitment_id.in_(commit_ids)),
        delete(ReputationEvent).where(ReputationEvent.user_id.in_(ids)),
        delete(Commitment).where(Commitment.id.in_(commit_ids)),
        delete(User).where(User.id.in_(ids)),
    ):
        await db.execute(stmt)
    await db.commit()


async def main() -> int:
    async with AsyncSessionLocal() as db:
        print("=" * 66)
        print("VOUCH — FULL LIFECYCLE SMOKE TEST (live DB)")
        print("=" * 66)
        await cleanup(db)

        # ── 0. Actors ───────────────────────────────────────────
        author = User(handle="smoke_lc_author", email="smoke_lc_author@test.dev")
        j1 = User(handle="smoke_lc_juror1", email="smoke_lc_j1@test.dev")
        j2 = User(handle="smoke_lc_juror2", email="smoke_lc_j2@test.dev")
        db.add_all([author, j1, j2])
        await db.commit()
        for u in (author, j1, j2):
            await db.refresh(u)
        A, J1, J2 = Principal(author), Principal(j1), Principal(j2)

        # ── 1. BEFORE snapshot ──────────────────────────────────
        print("\n[1] BEFORE — profile stats")
        before_author = (await u_router.get_user_profile(author.handle, db=db))["stats"]
        before_j1 = (await u_router.get_user_profile(j1.handle, db=db))["stats"]
        print(f"    author : rep={author.reputation_score} contributions={before_author['evidence_submitted']} "
              f"promises_tracked={before_author['commitments_authored']} votes_cast={before_author['total_votes_cast']}")
        print(f"    juror1 : rep={j1.reputation_score} contributions={before_j1['evidence_submitted']} "
              f"promises_tracked={before_j1['commitments_authored']} votes_cast={before_j1['total_votes_cast']}")

        # ── 2. Create ───────────────────────────────────────────
        print("\n[2] CREATE commitment (real falsifiability + juror validation)")
        created = await c_router.create_commitment(
            CommitmentCreate(
                title="Smoke: run 20km before the deadline",
                measurable_condition="Run exactly 20km in one week, verified via GPS app screenshots by the deadline",
                deadline=(datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
                juror_handles=[j1.handle, j2.handle],
            ),
            db=db, current_user=A,
        )
        cid = created.id
        print(f"    id={str(cid)[:8]}… status={created.status} jurors={created.juror_count}")

        # ── 3. Evidence ─────────────────────────────────────────
        print("\n[3] SUBMIT EVIDENCE (open -> evidence_submitted)")
        ev = await e_router.submit_evidence(
            cid, EvidenceCreate(type="text", content="Logged 12.4km on Monday and 7.8km on Wednesday — GPS screenshots attached."),
            db=db, current_user=A,
        )
        detail = await c_router.get_commitment(cid, db=db)
        print(f"    status now: {detail.status} | evidence rows: {detail.evidence_count}")

        # ── 4. Deadline job ─────────────────────────────────────
        print("\n[4] DEADLINE JOB (past-deadline evidence_submitted -> in_verification)")
        # Force the deadline into the past, then run the real job.
        c = await db.get(Commitment, cid)
        c.deadline = datetime.utcnow() - timedelta(hours=1)
        await db.commit()
        result = await check_deadlines(db)
        await db.refresh(c)
        print(f"    job result: {result} | status now: {c.status.value}")

        # ── 5. Votes ────────────────────────────────────────────
        print("\n[5] VOTES (juror1 met; juror2 met -> auto-resolve on final vote)")
        v1 = await cast_vote(cid, VoteCreate(vote="met", reason="Screenshots show 20.2km total."),
                             db=db, current_user=J1)
        await db.refresh(c)
        mid_status = c.status.value
        v2 = await cast_vote(cid, VoteCreate(vote="met", reason="Ran with her Sunday; distance checks out."),
                             db=db, current_user=J2)
        await db.refresh(c)
        print(f"    after vote 1: status={mid_status} (1 of 2 votes)")
        print(f"    after vote 2: status={c.status.value} resolved_at={c.resolved_at} (auto-resolved)")

        # ── 6. Reputation recompute job ─────────────────────────
        print("\n[6] REPUTATION RECOMPUTE (scheduled job pass)")
        events = (await db.execute(
            select(ReputationEvent).where(ReputationEvent.user_id.in_([author.id, j1.id, j2.id]))
        )).scalars().all()
        for e in events:
            who = "author" if e.user_id == author.id else ("juror1" if e.user_id == j1.id else "juror2")
            print(f"    event: {who:7s} delta={float(e.delta):+.1f} reason={e.reason.value}")
        new_author_rep = await recompute_reputation(db, author.id)
        new_j1_rep = await recompute_reputation(db, j1.id)
        new_j2_rep = await recompute_reputation(db, j2.id)
        await db.refresh(author); await db.refresh(j1); await db.refresh(j2)

        # ── 7. AFTER snapshot ───────────────────────────────────
        print("\n[7] AFTER — profile stats (same /users/{handle} query the rail uses)")
        after_author = (await u_router.get_user_profile(author.handle, db=db))["stats"]
        after_j1 = (await u_router.get_user_profile(j1.handle, db=db))["stats"]

        print("    author:")
        line("reputation_score", float(author.reputation_score), float(author.reputation_score) if False else new_author_rep)
        line("evidence_submitted (Contributions)", before_author["evidence_submitted"], after_author["evidence_submitted"])
        line("commitments_authored (Promises tracked)", before_author["commitments_authored"], after_author["commitments_authored"])
        line("commitments_total (met/broken)", before_author["commitments_total"], after_author["commitments_total"])
        print("    juror1:")
        line("reputation_score", float(j1.reputation_score), new_j1_rep)
        line("total_votes_cast", before_j1["total_votes_cast"], after_j1["total_votes_cast"])
        line("jury_accuracy", before_j1["jury_accuracy"], after_j1["jury_accuracy"])
        print("    juror2 reputation:", f"{new_j2_rep}")

        # ── 8. Verify the final state end-to-end ────────────────
        ok = (
            created.status == "open"
            and detail.status == "evidence_submitted"
            and mid_status == "in_verification"
            and c.status.value == "met"
            and after_author["evidence_submitted"] == before_author["evidence_submitted"] + 1
            and after_author["commitments_authored"] == before_author["commitments_authored"] + 1
            and after_author["commitments_total"] == before_author["commitments_total"] + 1
            and after_j1["total_votes_cast"] == before_j1["total_votes_cast"] + 1
            and len(events) == 3  # author kept + 2 accurate jurors
        )
        print("\n" + "=" * 66)
        print(f"RESULT: {'PASS' if ok else 'FAIL'} — full lifecycle exercised on the live DB")
        print("=" * 66)

        # ── 9. Cleanup (leave the DB as we found it) ────────────
        await cleanup(db)
        remaining = (await db.execute(select(User).where(User.handle.like("smoke_lc_%")))).scalars().all()
        print(f"cleanup: {'ok (test rows removed)' if not remaining else 'FAILED'}")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
