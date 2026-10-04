"""Alert ORM model representing targeted notifications for affected community members."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SeverityLevel

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.user import User


def generate_uuid() -> str:
    """Generate a UUID4 string identifier."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current datetime in UTC timezone."""
    return datetime.now(timezone.utc)


class Alert(Base):
    """Alert entity notifying an active user of an operational emergency in their vicinity."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_user_id_created_at", "user_id", "created_at"),
        Index("ix_alerts_incident_user", "incident_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    incident_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, native_enum=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="alerts")
    user: Mapped["User"] = relationship("User", back_populates="alerts")
