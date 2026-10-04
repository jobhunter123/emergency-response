"""Pydantic schemas for Incident entity."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EmergencyType, IncidentStatus, SeverityLevel


class IncidentResponse(BaseModel):
    """Response schema representing an aggregated emergency incident."""

    id: str
    emergency_type: EmergencyType
    title: str
    description: str | None = None
    severity: SeverityLevel
    status: IncidentStatus
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Incident center latitude between -90 and 90 degrees",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Incident center longitude between -180 and 180 degrees",
    )
    affected_radius_meters: float = Field(
        ...,
        ge=50.0,
        le=50000.0,
        description="Estimated radius of affected area in meters (50m - 50,000m)",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Algorithmic corroboration score between 0 and 100",
    )
    corroboration_count: int = Field(
        ...,
        ge=0,
        description="Number of corroborated user reports linked to incident",
    )
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class Coordinates(BaseModel):
    """Geographic coordinate pair."""

    latitude: float
    longitude: float


class BoundingBox(BaseModel):
    """North, south, east, and west geographic bounding coordinates."""

    north: float
    south: float
    east: float
    west: float


class AffectedAreaResponse(BaseModel):
    """Geographic representation of an incident's affected area."""

    center: Coordinates
    radius_meters: float
    bounds: BoundingBox | None = None


class IncidentDetailResponse(IncidentResponse):
    """Detailed response schema for an individual incident including report count, confidence tier, and affected area."""

    report_count: int = Field(
        default=0, description="Total number of associated user reports"
    )
    confidence_level: str | None = Field(
        default=None,
        description="Human-readable confidence tier (LOW, MODERATE, HIGH, VERY_HIGH)",
    )
    affected_area: AffectedAreaResponse | None = Field(
        default=None,
        description="Geographic affected area definition with center and radius",
    )
    affected_user_count: int = Field(
        default=0,
        description="Aggregate count of potentially affected active users within the radius",
    )
    evidence_photos: list[str] = Field(
        default_factory=list,
        description="List of public evidence photo URLs attached to contributing reports",
    )
