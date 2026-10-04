"""Incident operational status lifecycle management and responder workflows."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.enums import IncidentStatus
from app.models.incident import Incident
from app.models.user import User
from app.services.alerts import create_incident_alerts


class UnauthorizedResponderError(Exception):
    """Raised when a non-responder user attempts an operational status action."""

    pass


class InvalidStatusTransitionError(Exception):
    """Raised when an invalid lifecycle state transition is requested."""

    pass


# Centralized valid operational state transition map
VALID_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.UNVERIFIED: {
        IncidentStatus.VERIFYING,
        IncidentStatus.FALSE_ALARM,
    },
    IncidentStatus.VERIFYING: {
        IncidentStatus.CONFIRMED,
        IncidentStatus.FALSE_ALARM,
    },
    IncidentStatus.CONFIRMED: {
        IncidentStatus.RESPONDING,
        IncidentStatus.FALSE_ALARM,
    },
    IncidentStatus.RESPONDING: {
        IncidentStatus.CONTAINED,
        IncidentStatus.FALSE_ALARM,
    },
    IncidentStatus.CONTAINED: {
        IncidentStatus.RESOLVED,
    },
    IncidentStatus.RESOLVED: set(),
    IncidentStatus.FALSE_ALARM: set(),
}


def update_incident_status(
    db: Session,
    incident: Incident,
    new_status: IncidentStatus,
    responder: User,
) -> Incident:
    """Update the operational status of an incident by an authorized responder.

    Enforces:
    1. Responder role authorization check.
    2. Lifecycle state machine validation.
    3. Timestamp tracking (setting confirmed_at on confirmation, updating updated_at).
    4. Database transaction safety.

    Args:
        db: SQLAlchemy database session.
        incident: Target Incident entity.
        new_status: Destination IncidentStatus.
        responder: Authenticated User initiating the transition.

    Returns:
        The updated Incident instance.

    Raises:
        UnauthorizedResponderError: If responder.is_responder is False.
        InvalidStatusTransitionError: If the requested transition violates the lifecycle.
    """
    if not responder.is_responder:
        raise UnauthorizedResponderError(
            "Forbidden. Only verified responders can update incident status"
        )

    allowed_targets = VALID_TRANSITIONS.get(incident.status, set())
    if new_status not in allowed_targets:
        raise InvalidStatusTransitionError(
            f"Invalid incident status transition: {incident.status.value} -> {new_status.value}"
        )

    now = datetime.now(timezone.utc)

    # Set confirmed_at timestamp only upon transitioning to CONFIRMED
    if new_status == IncidentStatus.CONFIRMED:
        incident.confirmed_at = now

    incident.status = new_status
    incident.updated_at = now

    try:
        db.add(incident)
        db.commit()
        db.refresh(incident)
    except Exception:
        db.rollback()
        raise

    # Trigger emergency alert generation for operationally significant statuses
    if new_status in (IncidentStatus.CONFIRMED, IncidentStatus.RESPONDING):
        try:
            create_incident_alerts(db=db, incident=incident)
        except Exception:
            # Do NOT block status changes if alert generation encounters a non-fatal issue
            pass

    return incident
