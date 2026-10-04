"""Schemas package exporting Pydantic request and response models."""

from app.schemas.alert import AlertResponse
from app.schemas.auth import LoginRequest, Token
from app.schemas.emergency_report import (
    EmergencyReportCreate,
    EmergencyReportResponse,
    EmergencyReportSubmissionResponse,
    IncidentSummary,
)
from app.schemas.incident import (
    AffectedAreaResponse,
    BoundingBox,
    Coordinates,
    IncidentDetailResponse,
    IncidentResponse,
)
from app.schemas.incident_status import IncidentStatusUpdate
from app.schemas.user import (
    UserCreate,
    UserLocationResponse,
    UserLocationUpdate,
    UserResponse,
)

__all__ = [
    "UserCreate",
    "UserResponse",
    "UserLocationUpdate",
    "UserLocationResponse",
    "EmergencyReportCreate",
    "EmergencyReportResponse",
    "EmergencyReportSubmissionResponse",
    "IncidentSummary",
    "IncidentResponse",
    "IncidentDetailResponse",
    "IncidentStatusUpdate",
    "Token",
    "LoginRequest",
    "AlertResponse",
    "AffectedAreaResponse",
    "Coordinates",
    "BoundingBox",
]
