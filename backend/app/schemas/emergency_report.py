"""Pydantic schemas for EmergencyReport entity."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EmergencyType, IncidentStatus, SeverityLevel


class EmergencyReportCreate(BaseModel):
    """Schema for submitting an individual emergency report."""

    emergency_type: EmergencyType
    description: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Detailed description of the emergency observation",
    )
    severity: SeverityLevel
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude coordinate between -90 and 90 degrees",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude coordinate between -180 and 180 degrees",
    )


class EmergencyReportResponse(BaseModel):
    """Response schema representing an emergency report."""

    id: str
    user_id: str
    incident_id: str | None = None
    emergency_type: EmergencyType
    description: str
    severity: SeverityLevel
    latitude: float
    longitude: float
    reported_at: datetime
    confidence_contribution: float
    is_independent: bool
    photo_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class IncidentSummary(BaseModel):
    """Compact summary of an incident linked to an emergency report."""

    id: str
    status: IncidentStatus
    confidence_score: float
    corroboration_count: int
    confidence_level: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EmergencyReportSubmissionResponse(BaseModel):
    """Combined response model returned upon successful report submission."""

    report: EmergencyReportResponse
    incident: IncidentSummary
