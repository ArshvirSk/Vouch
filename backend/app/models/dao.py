"""Phase 3 model — DAO proposal ingestion.

DAO proposals are imported into the source_documents pipeline so the same
Gemini extraction + moderator review flow applies. Each proposal row keeps the
external (DAO, proposal id) pair unique to make ingestion idempotent.
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, text, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DaoProposalStatus(str, enum.Enum):
    PENDING = "pending"      # imported, awaiting extraction/review
    IMPORTED = "imported"    # a source document was created from it
    REJECTED = "rejected"


class DaoProposal(Base):
    __tablename__ = "dao_proposals"
    __table_args__ = (
        # (dao_name, external_id) unique — ingestion is idempotent
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dao_name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    proposer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[DaoProposalStatus] = mapped_column(
        Enum(DaoProposalStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=DaoProposalStatus.PENDING,
        server_default=text("'pending'"),
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    source_document = relationship("SourceDocument")
