"""Alert creation, querying, and management services."""

from datetime import datetime, timezone
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.enums import IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.user import User
from app.services.affected_area import find_affected_users

logger = logging.getLogger(__name__)


class AlertNotFoundError(Exception):
    """Raised when an alert record cannot be found."""

    pass


class AlertForbiddenError(Exception):
    """Raised when an unauthorized user attempts to access or modify an alert."""

    pass


def generate_alert_content(incident: Incident) -> tuple[str, str]:
    """Generate concise, deterministic title and message for an emergency alert.

    Adapts emergency type and severity level without external AI services.

    Args:
        incident: Target Incident entity.

    Returns:
        Tuple of (title, message).
    """
    type_display = incident.emergency_type.value.capitalize()
    type_lower = incident.emergency_type.value.lower()

    if incident.severity == SeverityLevel.CRITICAL:
        title = f"CRITICAL Alert: {type_display}"
        message = (
            f"A critical {type_lower} emergency has been confirmed near your location. "
            "Please take immediate precautions and follow official responder instructions."
        )
    else:
        title = f"Emergency Alert: {type_display}"
        message = (
            f"A confirmed {type_lower} has been reported near your location. "
            "Please stay alert and follow official responder instructions."
        )

    return title, message


def create_incident_alerts(db: Session, incident: Incident) -> list[Alert]:
    """Create emergency alerts for all active users within the incident's affected area.

    Enforces:
    1. Operational status gate: Only CONFIRMED or RESPONDING incidents generate alerts.
    2. Active user filter: Only active users with recorded locations within radius are alerted.
    3. Idempotency: Prevents duplicate alerts for the same (incident_id, user_id) pair.
    4. Database transaction safety.

    Args:
        db: SQLAlchemy database session.
        incident: Target Incident entity.

    Returns:
        List of newly created Alert entities.
    """
    if incident.status not in (IncidentStatus.CONFIRMED, IncidentStatus.RESPONDING):
        return []

    affected_users = find_affected_users(db=db, incident=incident)
    if not affected_users:
        return []

    # Retrieve existing alert recipient user IDs for this incident to guarantee idempotency
    existing_stmt = select(Alert.user_id).where(Alert.incident_id == incident.id)
    already_alerted_ids = set(db.execute(existing_stmt).scalars().all())

    title, message = generate_alert_content(incident)
    new_alerts: list[Alert] = []

    for user in affected_users:
        if user.id in already_alerted_ids:
            continue

        alert = Alert(
            incident_id=incident.id,
            user_id=user.id,
            title=title,
            message=message,
            severity=incident.severity,
            is_read=False,
        )
        db.add(alert)
        new_alerts.append(alert)

    if new_alerts:
        try:
            db.commit()
            for alert in new_alerts:
                db.refresh(alert)
        except Exception as exc:
            db.rollback()
            logger.error("Failed to commit alerts for incident %s: %s", incident.id, exc)
            raise

    return new_alerts


def get_user_alerts(
    db: Session,
    user_id: str,
    unread_only: bool = False,
) -> list[Alert]:
    """Retrieve emergency alerts for a specific authenticated user, newest first.

    Args:
        db: SQLAlchemy database session.
        user_id: ID of the recipient user.
        unread_only: When True, only unread alerts are returned.

    Returns:
        List of Alert entities ordered by created_at descending.
    """
    stmt = select(Alert).where(Alert.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Alert.is_read.is_(False))

    stmt = stmt.order_by(Alert.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def mark_alert_as_read(
    db: Session,
    alert_id: str,
    current_user: User,
) -> Alert:
    """Mark a user's alert as read and record the timestamp.

    Args:
        db: SQLAlchemy database session.
        alert_id: ID of the target alert.
        current_user: Authenticated user attempting the operation.

    Returns:
        The updated Alert entity.

    Raises:
        AlertNotFoundError: If the alert does not exist.
        AlertForbiddenError: If the alert belongs to another user.
    """
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise AlertNotFoundError(f"Alert with id '{alert_id}' not found")

    if alert.user_id != current_user.id:
        raise AlertForbiddenError("Forbidden. Cannot modify another user's alert")

    if not alert.is_read:
        alert.is_read = True
        alert.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)

    return alert
