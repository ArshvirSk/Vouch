import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EvidenceType(str, enum.Enum):
    """evidence_type enum — TRD §3."""
    LINK = "link"
    IMAGE = "image"
    TEXT = "text"
    ONCHAIN_TX = "onchain_tx"


class Evidence(Base):
    """Evidence table — TRD §3."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    commitment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commitments.id"), nullable=False
    )
    submitter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    type: Mapped[EvidenceType] = mapped_column(Enum(EvidenceType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)  # URL, storage path, or raw text
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=text("now()"),
    )

    # Relationships
    commitment = relationship("Commitment", back_populates="evidence")
    submitter = relationship("User", lazy="selectin")
