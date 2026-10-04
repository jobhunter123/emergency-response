"""Pydantic schema for operational incident status updates."""

from pydantic import BaseModel, Field

from app.models.enums import IncidentStatus


class IncidentStatusUpdate(BaseModel):
    """Schema for updating an incident's operational lifecycle status."""

    status: IncidentStatus = Field(
        ...,
        description="Target lifecycle status (e.g., VERIFYING, CONFIRMED, RESPONDING, CONTAINED, RESOLVED, FALSE_ALARM)",
    )
