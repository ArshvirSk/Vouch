import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Index, text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class VoteChoice(str, enum.Enum):
    """vote_choice enum — TRD §3."""
    MET = "met"
    BROKEN = "broken"
    ABSTAIN = "abstain"


class Vote(Base):
    """Votes table — TRD §3."""

    __tablename__ = "votes"
    __table_args__ = (
        Index("ix_votes_commitment_juror", "commitment_id", "juror_id", unique=True),
        Index("ix_votes_commitment_id", "commitment_id"),
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
    vote: Mapped[VoteChoice] = mapped_column(Enum(VoteChoice, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    voted_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    commitment = relationship("Commitment", back_populates="votes")
    juror = relationship("User", lazy="selectin")
