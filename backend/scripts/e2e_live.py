"""End-to-end live-DB validation for the Vouch platform.

Exercises the full pipeline against the real (Supabase) Postgres:
users → commitment → evidence → milestones (submit/verify) → source
submission → LIVE Gemini extraction → moderator approval → publication +
contradiction detection → jury pool → selection → votes → resolution →
reputation → milestone due/missed pass → anchoring jobs (no-op when chain
is not configured).

Router functions are called directly with a fake principal because Privy
JWTs cannot be minted locally; HTTP wiring is covered by TestClient tests.

Run: cd backend && python -m scripts.e2e_live
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.commitment import Commitment, CommitmentJuror, CommitmentStatus, JuryPool
from app.models.evidence import Evidence
from app.models.vote import Vote
from app.models.reputation import ReputationEvent
from app.models.notification import Notification
from app.models.milestone import Milestone, MilestoneStatus
from app.models.source import SourceDocument, SourceStatus, ExtractedCommitment, ExtractionStatus
from app.models.dao import DaoProposal
from app.routers import commitments as c_router
from app.routers import evidence as e_router
from app.routers import milestones as m_router
from app.routers import sources as s_router
from app.routers import dao as d_router
from app.routers import votes as v_router
from app.services.jury_resolution import resolve_commitment
from app.services.milestone_service import check_milestones
from app.tasks.jury_selection import select_public_juries
from app.schemas import (
    CommitmentCreate,
    EvidenceCreate,
    SourceDocumentCreate,
    ExtractionReviewRequest,
    SourceReviewRequest,
    VoteCreate,
)
from app.routers.milestones import (
    MilestoneCreate,
    MilestoneStatusUpdate,
)
from app.routers.dao import DaoProposalCreate


class Principal:
    def __init__(self, user: User):
        self.id = user.id
        self.handle = user.handle
        self.is_moderator = user.is_moderator


def ok(label: str, cond: bool, extra: str = "") -> bool:
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {label}{(' — ' + extra) if extra else ''}")
    return cond


async def cleanup(db, handle_prefix: str = "e2e_"):
    """Delete any prior e2e artifacts (ordered by FK dependencies)."""
    rows = (await db.execute(select(User).where(User.handle.like(f"{handle_prefix}%")))).scalars().all()
    ids = [u.id for u in rows]
    if not ids:
        return
    for stmt in (
        delete(Vote).where(Vote.commitment_id.in_(select(Commitment.id).where(Commitment.author_id.in_(ids)))),
        delete(Vote).where(Vote.juror_id.in_(ids)),
        delete(Evidence).where(Evidence.submitter_id.in_(ids)),
        delete(CommitmentJuror).where(CommitmentJuror.juror_id.in_(ids)),
        delete(JuryPool).where(JuryPool.user_id.in_(ids)),
        delete(Milestone).where(Milestone.commitment_id.in_(select(Commitment.id).where(Commitment.author_id.in_(ids)))),
        delete(Notification).where(Notification.user_id.in_(ids)),
        delete(ReputationEvent).where(ReputationEvent.user_id.in_(ids)),
        delete(ReputationEvent).where(ReputationEvent.commitment_id.in_(select(Commitment.id).where(Commitment.author_id.in_(ids)))),
        delete(ExtractedCommitment).where(ExtractedCommitment.source_id.in_(select(SourceDocument.id).where(SourceDocument.submitted_by_id.in_(ids)))),
        delete(SourceDocument).where(SourceDocument.submitted_by_id.in_(ids)),
        delete(DaoProposal).where(DaoProposal.dao_name.like("e2e-dao%")),
        delete(Commitment).where(Commitment.author_id.in_(ids)),
        delete(User).where(User.id.in_(ids)),
    ):
        await db.execute(stmt)
    await db.commit()


async def main() -> int:
    results: list[bool] = []
    suffix = uuid.uuid4().hex[:6]
    P = f"e2e_{suffix}_"

    async with AsyncSessionLocal() as db:
        print("=" * 64)
        print("VOUCH — LIVE DATABASE END-TO-END VALIDATION")
        print("=" * 64)

        print("\n[0] Cleaning prior e2e artifacts...")
        await cleanup(db, "e2e_")
        print("  done.")

        # ── 1. Users ────────────────────────────────────────────
        print("\n[1] Creating users (author, 2 jurors, moderator)...")
        author = User(handle=f"{P}alice", email=f"{P}alice@t.dev")
        juror1 = User(handle=f"{P}bob", email=f"{P}bob@t.dev")
        juror2 = User(handle=f"{P}carol", email=f"{P}carol@t.dev")
        moderator = User(handle=f"{P}mod", email=f"{P}mod@t.dev", is_moderator=True)
        db.add_all([author, juror1, juror2, moderator])
        await db.commit()
        for u in (author, juror1, juror2, moderator):
            await db.refresh(u)
        results.append(ok("4 users created", all(u.id for u in (author, juror1, juror2, moderator))))

        a, j1, j2, mod = Principal(author), Principal(juror1), Principal(juror2), Principal(moderator)

        # ── 2. Commitment + evidence ────────────────────────────
        print("\n[2] Creating a private commitment (2 jurors) + evidence...")
        future = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        created = await c_router.create_commitment(
            CommitmentCreate(
                title="E2E: finish the audit",
                measurable_condition="Complete exactly 12 audit checklist items by the deadline, verified by the shared checklist doc",
                deadline=future,
                juror_handles=[juror1.handle, juror2.handle],
            ),
            db=db, current_user=a,
        )
        results.append(ok(
            "commitment created",
            created.status == CommitmentStatus.OPEN.value and created.juror_count == 2,
            f"status={created.status}, jurors={created.juror_count}",
        ))
        cid = created.id

        ev = await e_router.submit_evidence(
            cid, EvidenceCreate(type="text", content="Checklist items 1-6 completed today."),
            db=db, current_user=a,
        )
        results.append(ok("evidence submitted", bool(ev.content_hash), f"type={ev.type}"))

        detail = await c_router.get_commitment(cid, db=db)
        results.append(ok(
            "status transitioned to evidence_submitted",
            detail.status == CommitmentStatus.EVIDENCE_SUBMITTED.value, detail.status,
        ))

        # ── 3. Milestones ───────────────────────────────────────
        print("\n[3] Milestones: create → submit → verify → progress...")
        await m_router.create_milestone(cid, MilestoneCreate(title="Draft chapter 1", progress_weight=1.0), db=db, current_user=a)
        await m_router.create_milestone(cid, MilestoneCreate(title="Draft chapter 2", progress_weight=3.0), db=db, current_user=a)
        listing = await m_router.list_milestones(cid, db=db)
        results.append(ok("2 milestones created, progress 0", listing.total_count == 2 and listing.progress == 0.0))

        m1 = listing.milestones[0]
        await m_router.submit_milestone(cid, m1.id, db=db, current_user=a)
        try:
            await m_router.verify_milestone(cid, m1.id, MilestoneStatusUpdate(decision="verified"), db=db, current_user=a)
            results.append(ok("author self-verification blocked", False))
        except Exception:
            results.append(ok("author self-verification blocked", True))

        verified = await m_router.verify_milestone(cid, m1.id, MilestoneStatusUpdate(decision="verified"), db=db, current_user=j1)
        listing = await m_router.list_milestones(cid, db=db)
        results.append(ok(
            "juror verified milestone; weighted progress 0.25",
            verified.status == "verified" and abs(listing.progress - 0.25) < 1e-6,
            f"progress={listing.progress}",
        ))

        # ── 4. Source → LIVE Gemini extraction → approval ──────
        print("\n[4] Phase 4 pipeline: source → LIVE Gemini extraction → review → publish...")
        src = await s_router.submit_source(
            SourceDocumentCreate(
                title=f"E2E debate transcript {suffix}",
                source_type="transcript",
                content=(
                    f"{author.handle} took the stage and made two concrete promises: first, our team will "
                    "publish 4 quarterly transparency reports by December 2027; second, I will personally "
                    "fund 2 university scholarships every year starting next fall. The crowd was thrilled."
                ),
            ),
            db=db, current_user=a,
        )
        results.append(ok("source submitted", src.status == SourceStatus.PENDING.value))

        extracted = await s_router.run_extraction(src.id, db=db, current_user=mod)
        n_drafts = len(extracted.extractions)
        results.append(ok(
            "LIVE Gemini extraction ran", n_drafts >= 1,
            f"{n_drafts} draft(s), source status={extracted.status}",
        ))

        if n_drafts:
            # Point the first draft at a real Vouch handle (moderator correction step)
            ext = extracted.extractions[0]
            e_row = await db.get(ExtractedCommitment, ext.id)
            e_row.subject_name = author.handle
            await db.commit()

            published = await s_router.review_extraction(
                src.id, ext.id, ExtractionReviewRequest(decision="approved"),
                db=db, current_user=mod,
            )
            results.append(ok(
                "extraction approved → public commitment published",
                published.status == ExtractionStatus.APPROVED.value and published.commitment_id is not None,
                f"commitment={str(published.commitment_id)[:8]}...",
            ))
            flags = await s_router.list_contradictions(status_filter=None, limit=50, offset=0, db=db)
            results.append(ok("contradiction scan executed post-publish", True, f"open flags so far: {len(flags)}"))

        # ── 5. DAO ingestion ────────────────────────────────────
        print("\n[5] Phase 3 DAO ingestion: import → to-source (idempotency)...")
        prop = await d_router.import_proposal(
            DaoProposalCreate(
                dao_name=f"e2e-dao-{suffix}", external_id="prop-1",
                title="Fund the community garden",
                description="The DAO will allocate 5000 tokens from the treasury to build the community garden by June 2027.",
                proposer=author.handle,
            ),
            db=db, current_user=a,
        )
        prop_again = await d_router.import_proposal(
            DaoProposalCreate(
                dao_name=f"e2e-dao-{suffix}", external_id="prop-1",
                title="Fund the community garden",
                description="The DAO will allocate 5000 tokens from the treasury to build the community garden by June 2027.",
            ),
            db=db, current_user=a,
        )
        results.append(ok("DAO proposal import idempotent", prop.id == prop_again.id))

        conv1 = await d_router.proposal_to_source(prop.id, db=db, current_user=mod)
        conv2 = await d_router.proposal_to_source(prop.id, db=db, current_user=mod)
        results.append(ok("to-source conversion + idempotent re-run", conv1.id == conv2.id, f"source={str(conv1.id)[:8]}..."))

        # ── 6. Jury pool → selection → votes → resolution ──────
        print("\n[6] Verification flow: pool → selection → votes → resolution → reputation...")
        pub = Commitment(
            author_id=author.id,
            title="E2E public pledge",
            measurable_condition="Publish exactly 3 open-source releases by the deadline, verified via GitHub tags",
            deadline=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),  # past → selectable
            content_hash=__import__('hashlib').sha256(f"e2e-{suffix}".encode()).hexdigest(),
            is_public=True,
            jury_pool_size=3,
        )
        db.add(pub)
        await db.flush()
        # Three pool members (schema minimum: jury_pool_size >= 3, quorum gate: >= 3)
        db.add(JuryPool(commitment_id=pub.id, user_id=juror1.id, staked_amount=2.0))
        db.add(JuryPool(commitment_id=pub.id, user_id=juror2.id, staked_amount=1.0))
        db.add(JuryPool(commitment_id=pub.id, user_id=moderator.id, staked_amount=0.5))
        await db.commit()

        await select_public_juries()
        await db.refresh(pub)
        jurors_now = (await db.execute(
            select(CommitmentJuror).where(CommitmentJuror.commitment_id == pub.id)
        )).scalars().all()
        results.append(ok("stake/reputation-weighted jury selected from pool", len(jurors_now) == 3))

        # Push to in_verification and vote
        pub.status = CommitmentStatus.IN_VERIFICATION
        await db.commit()
        for juror, choice in ((juror1, "met"), (juror2, "met"), (moderator, "met")):
            await v_router.cast_vote(
                pub.id, VoteCreate(vote=choice, reason="tags visible"),
                db=db, current_user=Principal(juror),
            )
        await db.refresh(pub)
        results.append(ok("unanimous votes → resolved as met", pub.status == CommitmentStatus.MET, pub.status.value))

        all_ids = [author.id, juror1.id, juror2.id, moderator.id]
        rep = (await db.execute(
            select(ReputationEvent).where(ReputationEvent.user_id.in_(all_ids))
        )).scalars().all()
        # author(kept) + 3 accurate jurors
        results.append(ok("reputation events emitted (author + jurors)", len(rep) >= 4, f"{len(rep)} events"))

        # ── 7. Milestone service pass + jobs ────────────────────
        print("\n[7] Scheduled-job passes (milestones, deadline worker, anchoring no-op)...")
        ms_result = await check_milestones(db)
        results.append(ok("milestone due/missed pass ran", isinstance(ms_result, dict), str(ms_result)))

        from app.tasks.anchor import anchor_pending_commitments
        await anchor_pending_commitments()  # chain unconfigured → logged no-op
        results.append(ok("batch anchoring job safe without chain config", True))

        from app.tasks.anchor_reputation import anchor_reputations
        rep_result = await anchor_reputations()  # chain unconfigured → attested=0
        results.append(ok("reputation anchoring job safe without chain config", rep_result.get("attested") == 0, str(rep_result)))

        # ── 8. Cleanup ──────────────────────────────────────────
        print("\n[8] Cleaning up e2e artifacts...")
        await cleanup(db, "e2e_")
        remaining = (await db.execute(select(User).where(User.handle.like("e2e_%")))).scalars().all()
        results.append(ok("database restored to pre-test state", len(remaining) == 0))

    passed, total = sum(results), len(results)
    print("\n" + "=" * 64)
    print(f"RESULT: {passed}/{total} checks passed")
    print("=" * 64)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
