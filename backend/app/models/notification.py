import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Enum, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class NotificationType(str, enum.Enum):
    INVITE = "INVITE"
    DEADLINE_WARNING = "DEADLINE_WARNING"
    VOTE_OPEN = "VOTE_OPEN"
    VOTE_REMINDER = "VOTE_REMINDER"
    RESOLUTION = "RESOLUTION"
    MILESTONE_DUE = "MILESTONE_DUE"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=text("now()"),
    )

    # Relationships
    user = relationship("User")
