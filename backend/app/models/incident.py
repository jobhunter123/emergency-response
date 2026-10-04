"""Incident ORM model representing aggregated real-world emergency events."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EmergencyType, IncidentStatus, SeverityLevel

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.emergency_report import EmergencyReport


def generate_uuid() -> str:
    """Generate a UUID4 string identifier."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current datetime in UTC timezone."""
    return datetime.now(timezone.utc)


class Incident(Base):
    """Incident entity grouping related individual emergency reports."""

    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 100.0",
            name="check_confidence_score_range",
        ),
        Index("ix_incidents_lat_lon", "latitude", "longitude"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    emergency_type: Mapped[EmergencyType] = mapped_column(
        SQLEnum(EmergencyType, native_enum=False),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, native_enum=False),
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        SQLEnum(IncidentStatus, native_enum=False),
        default=IncidentStatus.UNVERIFIED,
        index=True,
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
    affected_radius_meters: Mapped[float] = mapped_column(
        Float,
        default=500.0,
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    corroboration_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    reports: Mapped[list["EmergencyReport"]] = relationship(
        "EmergencyReport",
        back_populates="incident",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="incident",
        cascade="all, delete-orphan",
    )
