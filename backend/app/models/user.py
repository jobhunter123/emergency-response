"""User ORM model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.emergency_report import EmergencyReport


def generate_uuid() -> str:
    """Generate a UUID4 string identifier."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return the current datetime in UTC timezone."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account entity representing a community reporter or emergency responder."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    phone_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_responder: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    location_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    reports: Mapped[list["EmergencyReport"]] = relationship(
        "EmergencyReport",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="user",
        cascade="all, delete-orphan",
    )
