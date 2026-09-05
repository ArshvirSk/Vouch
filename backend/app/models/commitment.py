import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Index, text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CommitmentStatus(str, enum.Enum):
    """commitment_status enum — TRD §3."""
    OPEN = "open"
    EVIDENCE_SUBMITTED = "evidence_submitted"
    IN_VERIFICATION = "in_verification"
    MET = "met"
    BROKEN = "broken"
    DISPUTED = "disputed"
    EXPIRED = "expired"


class Commitment(Base):
    """Commitments table — TRD §3."""

    __tablename__ = "commitments"
    __table_args__ = (
        Index("ix_commitments_author_status", "author_id", "status"),
        Index("ix_commitments_deadline", "deadline"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    measurable_condition: Mapped[str] = mapped_column(String, nullable=False)
    deadline: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[CommitmentStatus] = mapped_column(
        Enum(CommitmentStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=CommitmentStatus.OPEN,
        server_default=text("'open'"),
    )
    # sha256(title+description+condition+deadline) — for future on-chain anchoring
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    onchain_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    author = relationship("User", back_populates="commitments", lazy="selectin")
    jurors = relationship("CommitmentJuror", back_populates="commitment", lazy="selectin")
    evidence = relationship("Evidence", back_populates="commitment", lazy="selectin")
    votes = relationship("Vote", back_populates="commitment", lazy="selectin")


class CommitmentJuror(Base):
    """Commitment jurors mapping — TRD §3."""

    __tablename__ = "commitment_jurors"
    __table_args__ = (
        Index("ix_commitment_jurors_unique", "commitment_id", "juror_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    commitment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commitments.id"), nullable=False
    )
    juror_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    invited_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    commitment = relationship("Commitment", back_populates="jurors")
    juror = relationship("User", lazy="selectin")
