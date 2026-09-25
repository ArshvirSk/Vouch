"""DAO router — Phase 3: On-chain Data Ingestion.

Imports commitments directly from DAO proposal data. Proposals land in the
`dao_proposals` table (idempotent on (dao_name, external_id)) and can then be
converted into a `source_documents` row — which feeds the existing Phase 4
pipeline: Gemini extraction → moderator review → public commitment →
automatic contradiction detection.

Endpoints:
  POST /dao/proposals                — import one proposal (authenticated)
  GET  /dao/proposals                — list imported proposals (public)
  POST /dao/proposals/{id}/to-source — moderator: push into the Phase 4 queue
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_moderator
from app.database import get_db
from app.models.dao import DaoProposal, DaoProposalStatus
from app.models.source import SourceDocument, SourceStatus, SourceType
from app.models.user import User
from app.schemas import SourceDocumentResponse

router = APIRouter(prefix="/dao", tags=["dao"])


class DaoProposalCreate(BaseModel):
    dao_name: str = Field(..., min_length=2, max_length=200)
    external_id: str = Field(..., min_length=1, max_length=300)
    title: str = Field(..., min_length=3, max_length=300)
    description: str | None = Field(None, min_length=20)
    url: str | None = None
    proposer: str | None = Field(None, max_length=200)


class DaoProposalResponse(BaseModel):
    id: uuid.UUID
    dao_name: str
    external_id: str
    title: str
    description: str | None
    url: str | None
    proposer: str | None
    status: str
    source_document_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/proposals", response_model=DaoProposalResponse, status_code=status.HTTP_201_CREATED)
async def import_proposal(
    req: DaoProposalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import a DAO proposal into the ingestion table.

    Idempotent: re-importing the same (dao_name, external_id) pair returns the
    existing row instead of duplicating it.
    """
    existing = await db.execute(
        select(DaoProposal).where(
            DaoProposal.dao_name == req.dao_name,
            DaoProposal.external_id == req.external_id,
        )
    )
    existing_proposal = existing.scalar_one_or_none()
    if existing_proposal:
        return existing_proposal

    proposal = DaoProposal(
        dao_name=req.dao_name,
        external_id=req.external_id,
        title=req.title,
        description=req.description,
        url=req.url,
        proposer=req.proposer,
        status=DaoProposalStatus.PENDING,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return proposal


@router.get("/proposals")
async def list_proposals(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List imported DAO proposals (public — ingestion transparency)."""
    query = select(DaoProposal)
    if status_filter:
        try:
            query = query.where(DaoProposalStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(DaoProposal.created_at.desc()).limit(limit).offset(offset)
    )
    proposals = list(result.scalars().all())

    return {
        "proposals": [
            {
                "id": str(p.id),
                "dao_name": p.dao_name,
                "external_id": p.external_id,
                "title": p.title,
                "description": p.description,
                "url": p.url,
                "proposer": p.proposer,
                "status": p.status.value,
                "source_document_id": str(p.source_document_id) if p.source_document_id else None,
                "created_at": p.created_at.isoformat(),
            }
            for p in proposals
        ],
        "total": total,
    }


@router.post("/proposals/{proposal_id}/to-source", response_model=SourceDocumentResponse)
async def proposal_to_source(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator),
):
    """Convert a DAO proposal into a source document, pushing it into the
    Phase 4 extraction + moderation pipeline. Idempotent: proposals that
    already have a source document return that document."""
    proposal = await db.get(DaoProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="DAO proposal not found")

    if proposal.source_document_id:
        source = await db.get(SourceDocument, proposal.source_document_id)
        if source:
            return source

    content_parts = [
        f"DAO: {proposal.dao_name}",
        f"Proposal: {proposal.title}",
    ]
    if proposal.proposer:
        content_parts.append(f"Proposer: {proposal.proposer}")
    if proposal.description:
        content_parts.append(f"Description: {proposal.description}")
    if proposal.url:
        content_parts.append(f"Reference: {proposal.url}")

    source = SourceDocument(
        title=f"[DAO] {proposal.dao_name}: {proposal.title}"[:300],
        source_type=SourceType.OTHER,
        source_url=proposal.url,
        content="\n".join(content_parts),
        status=SourceStatus.PENDING,
        submitted_by_id=current_user.id,
    )
    db.add(source)
    await db.flush()

    proposal.status = DaoProposalStatus.IMPORTED
    proposal.source_document_id = source.id

    await db.commit()
    await db.refresh(source)
    from app.routers.sources import _source_to_response
    return _source_to_response(source)
