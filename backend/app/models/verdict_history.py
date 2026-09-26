"""Verdict history — Stage 2 of the civic detail redesign.

Append-only snapshot of the public vote tally, written on every vote,
evidence submission, and commitment status transition for civic
commitments. Powers the "Public Verdict Over Time" chart. This is a real
schema addition, not derivable from the final votes table.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VerdictHistory(Base):
    """One row per tally-changing event, append-only."""

    __tablename__ = "verdict_history"
    __table_args__ = (
        Index("ix_verdict_history_commitment_time", "commitment_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    commitment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False
    )
    met_count: Mapped[int] = mapped_column(nullable=False, default=0)
    broken_count: Mapped[int] = mapped_column(nullable=False, default=0)
    abstain_count: Mapped[int] = mapped_column(nullable=False, default=0)
    juror_count: Mapped[int] = mapped_column(nullable=False, default=0)
    # Free-text label shown as an annotated marker on the chart,
    # e.g. "News: Work starts", "Citizen report: poor work", "Voting opened".
    event_label: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # 'vote' | 'evidence' | 'status' | 'seed'
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, default="status")
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=text("now()"),
    )

    commitment = relationship("Commitment")
