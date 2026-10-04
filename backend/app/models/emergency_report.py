"""EmergencyReport ORM model representing individual user reports."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EmergencyType, SeverityLevel

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.user import User


def generate_uuid() -> str:
    """Generate a UUID4 string identifier."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current datetime in UTC timezone."""
    return datetime.now(timezone.utc)


class EmergencyReport(Base):
    """Individual emergency observation submitted by a user."""

    __tablename__ = "emergency_reports"
    __table_args__ = (
        Index("ix_emergency_reports_lat_lon", "latitude", "longitude"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    incident_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    emergency_type: Mapped[EmergencyType] = mapped_column(
        SQLEnum(EmergencyType, native_enum=False),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, native_enum=False),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(
        Float,
        index=True,
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(
        Float,
        index=True,
        nullable=False,
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )
    confidence_contribution: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    is_independent: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    photo_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        default=None,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="reports",
    )
    incident: Mapped["Incident | None"] = relationship(
        "Incident",
        back_populates="reports",
    )
