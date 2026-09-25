import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Numeric, ForeignKey, Index, text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ReputationReason(str, enum.Enum):
    """reputation_reason enum — TRD §3."""
    COMMITMENT_KEPT = "commitment_kept"
    COMMITMENT_BROKEN = "commitment_broken"
    JURY_ACCURATE = "jury_accurate"
    JURY_INACCURATE = "jury_inaccurate"


class ReputationEvent(Base):
    """Reputation events table — TRD §3.
    Append-only: events are never updated/deleted (TRD §6 auditability).
    """

    __tablename__ = "reputation_events"
    __table_args__ = (
        Index("ix_reputation_events_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    delta: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    reason: Mapped[ReputationReason] = mapped_column(Enum(ReputationReason, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("commitments.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=text("now()"),
    )

    # Relationships
    user = relationship("User", back_populates="reputation_events")
    commitment = relationship("Commitment", lazy="selectin")
