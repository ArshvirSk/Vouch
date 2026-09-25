"""Milestone tracking model — Phase 3.

Links a commitment to specific roadmap-style items with ongoing checks:
each milestone has a target date and a verification status that the
commitment's jurors (or a moderator) can update as evidence arrives.
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, text, Enum, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MilestoneStatus(str, enum.Enum):
    PENDING = "pending"          # not yet due / awaiting work
    SUBMITTED = "submitted"      # author claims completion, awaiting juror check
    VERIFIED = "verified"        # jurors confirmed completion
    MISSED = "missed"            # target date passed without verification


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    commitment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    detail: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[int] = mapped_column(default=0)  # ordering within the commitment
    progress_weight: Mapped[float] = mapped_column(Float, default=1.0)  # relative importance
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=MilestoneStatus.PENDING,
        server_default=text("'pending'"),
    )
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    commitment = relationship("Commitment", back_populates="milestones")
    verified_by = relationship("User")


# Allow the Commitment ORM object to carry milestones
from app.models.commitment import Commitment  # noqa: E402  (import cycle guard)

Commitment.milestones = relationship(
    "Milestone",
    back_populates="commitment",
    cascade="all, delete-orphan",
    lazy="selectin",
    order_by="Milestone.position",
)
