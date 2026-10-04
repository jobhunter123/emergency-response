"""Incidents router providing active incident listings, details, and responder status updates."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.enums import EmergencyType, SeverityLevel
from app.models.user import User
from app.schemas.incident import IncidentDetailResponse, IncidentResponse
from app.schemas.incident_status import IncidentStatusUpdate
from app.services.affected_area import (
    calculate_affected_area,
    count_affected_users,
)
from app.services.confidence import get_confidence_level
from app.services.emergency_report import (
    get_active_incidents,
    get_incident_by_id,
)
from app.services.incident_status import (
    InvalidStatusTransitionError,
    UnauthorizedResponderError,
    update_incident_status,
)

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get(
    "",
    response_model=list[IncidentResponse],
    summary="List active incidents",
    description="Retrieve all active emergency incidents (excluding resolved and false alarms) with optional type, severity, and spatial radius filters.",
    responses={
        200: {"description": "List of active emergency incidents."},
    },
)
def list_incidents(
    emergency_type: EmergencyType | None = Query(
        default=None, description="Filter by emergency type"
    ),
    severity: SeverityLevel | None = Query(
        default=None, description="Filter by severity level"
    ),
    latitude: float | None = Query(
        default=None, ge=-90.0, le=90.0, description="Center latitude for proximity filter"
    ),
    longitude: float | None = Query(
        default=None, ge=-180.0, le=180.0, description="Center longitude for proximity filter"
    ),
    radius_meters: float | None = Query(
        default=None, ge=1.0, description="Radius in meters from center coordinates"
    ),
    db: Session = Depends(get_db),
) -> list[IncidentResponse]:
    """Retrieve active emergency incidents for community map display."""
    incidents = get_active_incidents(
        db=db,
        emergency_type=emergency_type,
        severity=severity,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
    )
    return [IncidentResponse.model_validate(inc) for inc in incidents]


@router.get(
    "/{incident_id}",
    response_model=IncidentDetailResponse,
    summary="Retrieve incident details",
    description="Fetch details of a specific incident including the total count of corroborating reports and confidence tier.",
    responses={
        200: {"description": "Incident details retrieved."},
        404: {"description": "Incident not found."},
    },
)
def read_incident(
    incident_id: str,
    db: Session = Depends(get_db),
) -> IncidentDetailResponse:
    """Fetch details, corroborating report count, and confidence tier for a single incident."""
    incident = get_incident_by_id(db=db, incident_id=incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    response_data = IncidentResponse.model_validate(incident).model_dump()
    response_data["report_count"] = len(incident.reports)
    response_data["confidence_level"] = get_confidence_level(incident.confidence_score)
    response_data["affected_area"] = calculate_affected_area(incident)
    response_data["affected_user_count"] = count_affected_users(db=db, incident=incident)
    response_data["evidence_photos"] = [
        r.photo_url for r in incident.reports if r.photo_url
    ]
    return IncidentDetailResponse(**response_data)


@router.patch(
    "/{incident_id}/status",
    response_model=IncidentDetailResponse,
    summary="Update incident operational status",
    description="Advance an incident through its operational lifecycle (VERIFYING, CONFIRMED, RESPONDING, CONTAINED, RESOLVED, FALSE_ALARM). Requires authenticated responder authorization.",
    responses={
        200: {"description": "Incident operational status updated successfully."},
        400: {"description": "Invalid status transition."},
        401: {"description": "Authentication required. Bearer token missing or invalid."},
        403: {"description": "Forbidden. User is not an authorized responder."},
        404: {"description": "Incident not found."},
    },
)
def update_status(
    incident_id: str,
    status_update: IncidentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IncidentDetailResponse:
    """Update incident operational status with responder authorization and transition validation."""
    if not current_user.is_responder:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. Only authorized responders can update incident status",
        )

    incident = get_incident_by_id(db=db, incident_id=incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    try:
        updated_incident = update_incident_status(
            db=db,
            incident=incident,
            new_status=status_update.status,
            responder=current_user,
        )
    except InvalidStatusTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except UnauthorizedResponderError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    response_data = IncidentResponse.model_validate(updated_incident).model_dump()
    response_data["report_count"] = len(updated_incident.reports)
    response_data["confidence_level"] = get_confidence_level(
        updated_incident.confidence_score
    )
    response_data["affected_area"] = calculate_affected_area(updated_incident)
    response_data["affected_user_count"] = count_affected_users(
        db=db, incident=updated_incident
    )
    response_data["evidence_photos"] = [
        r.photo_url for r in updated_incident.reports if r.photo_url
    ]
    return IncidentDetailResponse(**response_data)
