"""Sources router — Phase 4: Public-Figure Accountability Skin.

Endpoints:
  POST /sources                        — submit a public statement to the queue
  GET  /sources                        — list the queue (public, read-only)
  POST /sources/{id}/extract           — run LLM extraction (moderator)
  POST /sources/{id}/review            — moderator source-level decision
  POST /sources/{id}/extractions/{eid}/review — approve → publishes a public commitment
  POST /sources/{id}/check-contradictions     — run AI contradiction detection
  GET  /contradictions                 — list open flags for community review
  POST /contradictions/{id}/review     — moderator confirm/dismiss

LLM features fail closed on disabled engine (explicit error), so moderators
never mistake a skipped AI pass for a clean one.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_moderator
from app.config import get_settings
from app.database import get_db
from app.models.commitment import Commitment, CommitmentStatus
from app.models.source import (
    ContradictionFlag,
    ContradictionStatus,
    ExtractedCommitment,
    ExtractionStatus,
    SourceDocument,
    SourceStatus,
    SourceType,
)
from app.models.user import User
from app.schemas import (
    ContradictionFlagResponse,
    ContradictionReviewRequest,
    ExtractionReviewRequest,
    ExtractedCommitmentResponse,
    SourceDocumentCreate,
    SourceDocumentListResponse,
    SourceDocumentResponse,
    SourceReviewRequest,
)
from app.services.llm import LLMDisabledError, llm_engine

router = APIRouter(tags=["sources"])
settings = get_settings()
logger = logging.getLogger(__name__)


def _source_to_response(source: SourceDocument) -> SourceDocumentResponse:
    return SourceDocumentResponse(
        id=source.id,
        title=source.title,
        source_type=source.source_type.value,
        source_url=source.source_url,
        content=source.content,
        published_at=source.published_at,
        status=source.status.value,
        created_at=source.created_at,
        reviewed_at=source.reviewed_at,
        extractions=[
            ExtractedCommitmentResponse(
                id=e.id,
                source_id=e.source_id,
                subject_name=e.subject_name,
                statement=e.statement,
                reformulated_condition=e.reformulated_condition,
                suggested_deadline=e.suggested_deadline,
                confidence=e.confidence,
                status=e.status.value,
                commitment_id=e.commitment_id,
            )
            for e in source.extractions
        ],
        model_config={"from_attributes": True},
    )


async def _get_source_or_404(db: AsyncSession, source_id: uuid.UUID) -> SourceDocument:
    source = await db.get(SourceDocument, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source document not found")
    return source


@router.post("/sources", response_model=SourceDocumentResponse, status_code=status.HTTP_201_CREATED)
async def submit_source(
    req: SourceDocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a public statement (news, transcript, speech, social post) to the
    moderation queue. Any authenticated user can submit; moderators review."""
    source = SourceDocument(
        title=req.title,
        source_type=SourceType(req.source_type),
        source_url=req.source_url,
        content=req.content,
        published_at=req.published_at,
        status=SourceStatus.PENDING,
        submitted_by_id=current_user.id,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return _source_to_response(source)


@router.get("/sources", response_model=SourceDocumentListResponse)
async def list_sources(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List the source queue (public read-only — transparency of moderation)."""
    query = select(SourceDocument)
    if status_filter:
        try:
            query = query.where(SourceDocument.status == SourceStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(SourceDocument.created_at.desc()).limit(limit).offset(offset)
    )
    sources = list(result.scalars().unique().all())

    return SourceDocumentListResponse(
        sources=[_source_to_response(s) for s in sources],
        total=total,
    )


@router.post("/sources/{source_id}/extract", response_model=SourceDocumentResponse)
async def run_extraction(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator),
):
    """Run LLM extraction over a source document. Idempotent: re-running
    replaces prior pending extractions."""
    source = await _get_source_or_404(db, source_id)

    try:
        result = llm_engine.extract_commitments(source.content)
    except LLMDisabledError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM extraction is not configured (set VOUCH_ENABLE_LLM_CHECK and VOUCH_GEMINI_API_KEY).",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM extraction failed: {e}",
        )

    # Replace prior pending extractions (approved ones are kept — they are history)
    for prior in source.extractions:
        if prior.status == ExtractionStatus.PENDING:
            await db.delete(prior)

    # Parse suggested deadlines defensively
    def _parse_deadline(raw: str | None):
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            return None

    drafts = result.commitments if result else []
    for d in drafts:
        db.add(ExtractedCommitment(
            source_id=source.id,
            subject_name=d.subject_name,
            statement=d.statement,
            reformulated_condition=d.reformulated_condition,
            suggested_deadline=_parse_deadline(d.suggested_deadline),
            confidence=float(d.confidence),
            status=ExtractionStatus.PENDING,
        ))

    source.status = SourceStatus.EXTRACTED if drafts else SourceStatus.REJECTED
    source.extraction_cache = {"drafts": [d.model_dump(mode="json") for d in drafts]}
    await db.commit()
    await db.refresh(source)
    return _source_to_response(source)


@router.post("/sources/{source_id}/review", response_model=SourceDocumentResponse)
async def review_source(
    source_id: uuid.UUID,
    req: SourceReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator),
):
    """Moderator decision on a source document (approve/reject)."""
    source = await _get_source_or_404(db, source_id)
    decision = SourceStatus(req.decision)
    source.status = decision
    source.reviewed_by_id = current_user.id
    source.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(source)
    return _source_to_response(source)


@router.post(
    "/sources/{source_id}/extractions/{extraction_id}/review",
    response_model=ExtractedCommitmentResponse,
)
async def review_extraction(
    source_id: uuid.UUID,
    extraction_id: uuid.UUID,
    req: ExtractionReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator),
):
    """Approve or reject an extracted commitment. Approval publishes it as a
    real public commitment with an open jury pool, then runs contradiction
    detection against the subject's existing public commitments."""
    source = await _get_source_or_404(db, source_id)
    extraction = await db.get(ExtractedCommitment, extraction_id)
    if not extraction or extraction.source_id != source.id:
        raise HTTPException(status_code=404, detail="Extraction not found")
    if extraction.status != ExtractionStatus.PENDING:
        raise HTTPException(status_code=409, detail="Extraction was already reviewed")
    if extraction.commitment_id:
        raise HTTPException(status_code=409, detail="Extraction already published")

    if req.decision == "rejected":
        extraction.status = ExtractionStatus.REJECTED
        await db.commit()
        await db.refresh(extraction)
        return ExtractedCommitmentResponse(
            id=extraction.id,
            source_id=extraction.source_id,
            subject_name=extraction.subject_name,
            statement=extraction.statement,
            reformulated_condition=extraction.reformulated_condition,
            suggested_deadline=extraction.suggested_deadline,
            confidence=extraction.confidence,
            status=extraction.status.value,
            commitment_id=extraction.commitment_id,
        )

    # ── Approve → publish as a public commitment ──
    # The subject must exist as a user on Vouch; we key on handle == subject_name
    result = await db.execute(
        select(User).where(func.lower(User.handle) == extraction.subject_name.strip().lower())
    )
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"No Vouch user with handle '{extraction.subject_name}'. "
                "The public figure must have a Vouch account before their promises can be tracked."
            ),
        )
    if subject.handle == current_user.handle:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Moderators cannot publish commitments attributed to themselves.",
        )

    # Deadline: use the LLM-suggested one if present and in the future,
    # otherwise default to 90 days from publication.
    now = datetime.now(timezone.utc)
    deadline = extraction.suggested_deadline
    if deadline is None or deadline <= now:
        deadline = now + timedelta(days=90)

    content_hash = hashlib.sha256(
        f"{extraction.statement}|{extraction.reformulated_condition}|{deadline.isoformat()}".encode()
    ).hexdigest()

    commitment = Commitment(
        author_id=subject.id,
        title=extraction.statement[:200],
        description=(
            f"Published from source '{source.title}' by moderator @{current_user.handle}. "
            f"Original statement: \"{extraction.statement}\""
        ),
        measurable_condition=extraction.reformulated_condition,
        deadline=deadline,
        content_hash=content_hash,
        is_public=True,
        jury_pool_size=settings.public_jury_pool_size,
    )
    db.add(commitment)
    await db.flush()

    extraction.status = ExtractionStatus.APPROVED
    extraction.commitment_id = commitment.id

    # Keep an audit trail of published extractions in the source cache
    source.status = SourceStatus.APPROVED

    # ── Contradiction detection: compare the new promise against the
    #    subject's recent public commitments ──
    ledger_result = await db.execute(
        select(Commitment)
        .where(
            Commitment.author_id == subject.id,
            Commitment.is_public == True,  # noqa: E712
            Commitment.id != commitment.id,
        )
        .order_by(Commitment.created_at.desc())
        .limit(settings.contradiction_ledger_size)
    )
    ledger = list(ledger_result.scalars().unique().all())

    if ledger and llm_engine.enabled and llm_engine.client:
        try:
            contradiction_result = llm_engine.find_contradictions(
                new_statement=extraction.statement,
                existing_commitments=[
                    {"title": c.title, "condition": c.measurable_condition} for c in ledger
                ],
            )
            for flag in contradiction_result.contradictions:
                idx = flag.commitment_index
                if 0 <= idx < len(ledger):
                    db.add(ContradictionFlag(
                        source_id=source.id,
                        extracted_commitment_id=extraction.id,
                        existing_commitment_id=ledger[idx].id,
                        explanation=flag.explanation,
                        confidence=float(flag.confidence),
                        status=ContradictionStatus.OPEN,
                    ))
        except Exception as e:
            # Contradiction detection is best-effort; never block publication
            logger.warning("Contradiction detection failed for source %s: %s", source.id, e)

    await db.commit()
    await db.refresh(extraction)
    return ExtractedCommitmentResponse(
        id=extraction.id,
        source_id=extraction.source_id,
        subject_name=extraction.subject_name,
        statement=extraction.statement,
        reformulated_condition=extraction.reformulated_condition,
        suggested_deadline=extraction.suggested_deadline,
        confidence=extraction.confidence,
        status=extraction.status.value,
        commitment_id=extraction.commitment_id,
    )


@router.get("/contradictions", response_model=list[ContradictionFlagResponse])
async def list_contradictions(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List contradiction flags for community review (public — transparency)."""
    query = select(ContradictionFlag)
    if status_filter:
        try:
            query = query.where(ContradictionFlag.status == ContradictionStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    result = await db.execute(
        query.order_by(ContradictionFlag.created_at.desc()).limit(limit).offset(offset)
    )
    flags = list(result.scalars().unique().all())
    return [
        ContradictionFlagResponse(
            id=f.id,
            source_id=f.source_id,
            extracted_commitment_id=f.extracted_commitment_id,
            existing_commitment_id=f.existing_commitment_id,
            explanation=f.explanation,
            confidence=f.confidence,
            status=f.status.value,
            created_at=f.created_at,
        )
        for f in flags
    ]


@router.post("/contradictions/{flag_id}/review", response_model=ContradictionFlagResponse)
async def review_contradiction(
    flag_id: uuid.UUID,
    req: ContradictionReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator),
):
    """Moderator confirms or dismisses an AI-flagged contradiction."""
    flag = await db.get(ContradictionFlag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Contradiction flag not found")
    if flag.status != ContradictionStatus.OPEN:
        raise HTTPException(status_code=409, detail="Flag was already reviewed")

    flag.status = ContradictionStatus(req.decision)
    await db.commit()
    await db.refresh(flag)
    return ContradictionFlagResponse(
        id=flag.id,
        source_id=flag.source_id,
        extracted_commitment_id=flag.extracted_commitment_id,
        existing_commitment_id=flag.existing_commitment_id,
        explanation=flag.explanation,
        confidence=flag.confidence,
        status=flag.status.value,
        created_at=flag.created_at,
    )
