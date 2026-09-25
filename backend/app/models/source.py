"""Phase 4 models — Public-Figure Accountability Skin.

- SourceDocument: a public statement (news, transcript, speech, social post)
  ingested into the moderation queue.
- ExtractedCommitment: one candidate promise the LLM pulled out of a source.
- ContradictionFlag: an AI-flagged conflict between a new statement and an
  existing commitment on the platform.
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, text, Enum, DateTime, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SourceType(str, enum.Enum):
    NEWS = "news"
    TRANSCRIPT = "transcript"
    SPEECH = "speech"
    SOCIAL_MEDIA = "social_media"
    OTHER = "other"


class SourceStatus(str, enum.Enum):
    PENDING = "pending"          # awaiting LLM extraction / review
    EXTRACTED = "extracted"      # extraction ran, awaiting moderator review
    APPROVED = "approved"        # at least one extraction approved & published
    REJECTED = "rejected"        # moderator rejected the source


class ExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"        # published as a real public commitment
    REJECTED = "rejected"


class ContradictionStatus(str, enum.Enum):
    OPEN = "open"                # awaiting community/moderator review
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(String, nullable=False)  # raw statement text
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=SourceStatus.PENDING,
        server_default=text("'pending'"),
    )
    extraction_cache: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # raw LLM output
    submitted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    # lazy="selectin" so relationships load eagerly (and safely) in async sessions
    extractions = relationship(
        "ExtractedCommitment", back_populates="source",
        cascade="all, delete-orphan", lazy="selectin",
    )
    contradictions = relationship(
        "ContradictionFlag", back_populates="source",
        cascade="all, delete-orphan", lazy="selectin",
    )


class ExtractedCommitment(Base):
    __tablename__ = "extracted_commitments"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False
    )
    subject_name: Mapped[str] = mapped_column(String(200), nullable=False)  # who made the promise
    statement: Mapped[str] = mapped_column(String, nullable=False)          # promise as stated
    reformulated_condition: Mapped[str] = mapped_column(String, nullable=False)  # falsifiable rewrite
    suggested_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ExtractionStatus.PENDING,
        server_default=text("'pending'"),
    )
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    source = relationship("SourceDocument", back_populates="extractions")
    published_commitment = relationship("Commitment")
    contradictions = relationship(
        "ContradictionFlag", back_populates="extracted_commitment", cascade="all, delete-orphan"
    )


class ContradictionFlag(Base):
    __tablename__ = "contradiction_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False
    )
    extracted_commitment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("extracted_commitments.id", ondelete="CASCADE"), nullable=False
    )
    existing_commitment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False
    )
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[ContradictionStatus] = mapped_column(
        Enum(ContradictionStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ContradictionStatus.OPEN,
        server_default=text("'open'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    source = relationship("SourceDocument", back_populates="contradictions")
    extracted_commitment = relationship("ExtractedCommitment", back_populates="contradictions")
    existing_commitment = relationship("Commitment")
