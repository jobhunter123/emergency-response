"""Pydantic schemas for User entity."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for registering or creating a new user."""

    email: EmailStr = Field(..., description="Unique user email address")
    password: str = Field(..., min_length=6, max_length=128, description="User password")
    full_name: str | None = Field(default=None, max_length=255, description="Full name")
    phone_number: str | None = Field(default=None, max_length=50, description="Contact phone number")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email string to lowercase."""
        return v.strip().lower()


class UserLocationUpdate(BaseModel):
    """Schema for updating user's current point-in-time geographic location."""

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="User latitude in degrees (-90 to 90)",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="User longitude in degrees (-180 to 180)",
    )


class UserLocationResponse(BaseModel):
    """Response schema for user location snapshot."""

    latitude: float
    longitude: float
    location_updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Public user response schema excluding password fields."""

    id: str
    email: str
    full_name: str | None = None
    phone_number: str | None = None
    is_active: bool
    is_responder: bool
    latitude: float | None = None
    longitude: float | None = None
    location_updated_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
