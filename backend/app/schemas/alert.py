"""Pydantic schemas for Alert entity."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SeverityLevel


class AlertResponse(BaseModel):
    """Schema representing an alert event returned to the frontend."""

    id: str
    incident_id: str
    title: str
    message: str
    severity: SeverityLevel
    created_at: datetime
    read_at: datetime | None = None
    is_read: bool

    model_config = ConfigDict(from_attributes=True)
