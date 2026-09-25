import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Numeric, text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    """Users table — TRD §3."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    handle: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Hybrid Auth Fields
    privy_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    wallet_address: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String, default="email", server_default=text("'email'"))
    reputation_score: Mapped[float] = mapped_column(
        Numeric(5, 2), default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=text("now()"),
    )
    current_streak: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    longest_streak: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    is_moderator: Mapped[bool] = mapped_column(default=False, server_default=text("false"))

    # Phase 3: native on-chain reputation attestation state
    onchain_score: Mapped[float | None] = mapped_column(nullable=True)
    onchain_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    onchain_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    commitments = relationship("Commitment", back_populates="author", lazy="selectin")
    reputation_events = relationship("ReputationEvent", back_populates="user", lazy="selectin")
