"""Emergency report business logic and preliminary incident grouping services."""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.emergency_report import EmergencyReport
from app.models.enums import EmergencyType, IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.user import User
from app.schemas.emergency_report import EmergencyReportCreate
from app.services.confidence import (
    calculate_incident_confidence,
    update_incident_status_from_confidence,
)
from app.services.geolocation import (
    calculate_distance_meters,
    is_within_radius,
)

# Time window for matching incoming reports against active incidents
INCIDENT_MATCH_WINDOW_MINUTES: int = 60

# Severity hierarchy for determining whether a report escalates an incident
SEVERITY_RANKS: dict[SeverityLevel, int] = {
    SeverityLevel.LOW: 1,
    SeverityLevel.MEDIUM: 2,
    SeverityLevel.HIGH: 3,
    SeverityLevel.CRITICAL: 4,
}


def find_matching_incident(
    db: Session,
    emergency_type: EmergencyType,
    latitude: float,
    longitude: float,
) -> Incident | None:
    """Find the nearest active incident matching type, recency, and radius.

    Matching criteria:
    1. Same emergency type.
    2. Status is active (not RESOLVED and not FALSE_ALARM).
    3. Created within INCIDENT_MATCH_WINDOW_MINUTES.
    4. Distance between report and incident <= incident.affected_radius_meters.

    Note:
    A match represents preliminary spatial/temporal clustering and does NOT imply
    official verification or established ground truth.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(
        minutes=INCIDENT_MATCH_WINDOW_MINUTES
    )

    statement = select(Incident).where(
        Incident.emergency_type == emergency_type,
        Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.FALSE_ALARM]),
        Incident.created_at >= cutoff_time,
    )
    candidates = db.scalars(statement).all()

    matching_incident: Incident | None = None
    min_distance: float = float("inf")

    for incident in candidates:
        distance = calculate_distance_meters(
            incident.latitude, incident.longitude, latitude, longitude
        )
        if distance <= incident.affected_radius_meters and distance < min_distance:
            min_distance = distance
            matching_incident = incident

    return matching_incident


def create_emergency_report(
    db: Session,
    user: User,
    report_data: EmergencyReportCreate,
    photo_url: str | None = None,
) -> tuple[EmergencyReport, Incident]:
    """Create an emergency report, cluster it into an incident, and recalculate confidence.

    Transactional safety:
    Creates or updates the incident, report, confidence score, and preliminary status atomically.
    On failure, rolls back.

    Domain note:
    confidence_score indicates dynamic corroboration signal across independent reports;
    it does NOT assert ground truth.
    UNVERIFIED status means pending corroboration; it does NOT mean the report is false.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(
        minutes=INCIDENT_MATCH_WINDOW_MINUTES
    )

    matching_incident = find_matching_incident(
        db=db,
        emergency_type=report_data.emergency_type,
        latitude=report_data.latitude,
        longitude=report_data.longitude,
    )

    try:
        if matching_incident is not None:
            incident = matching_incident

            # Check if this user has already reported this incident in the recency window
            existing_user_report = db.scalars(
                select(EmergencyReport).where(
                    EmergencyReport.incident_id == incident.id,
                    EmergencyReport.user_id == user.id,
                    EmergencyReport.reported_at >= cutoff_time,
                )
            ).first()

            if existing_user_report is not None:
                # Same user re-reporting: stored but not counted as independent corroboration
                is_independent = False
            else:
                is_independent = True
                incident.corroboration_count += 1

            # Escalate severity if the incoming report indicates greater severity
            if SEVERITY_RANKS.get(report_data.severity, 0) > SEVERITY_RANKS.get(
                incident.severity, 0
            ):
                incident.severity = report_data.severity

            incident.updated_at = datetime.now(timezone.utc)
        else:
            # Create a new Incident with default unverified status
            title = f"{report_data.emergency_type.value.replace('_', ' ').title()} Incident"
            incident = Incident(
                emergency_type=report_data.emergency_type,
                title=title,
                description=report_data.description,
                severity=report_data.severity,
                status=IncidentStatus.UNVERIFIED,
                latitude=report_data.latitude,
                longitude=report_data.longitude,
                affected_radius_meters=500.0,
                confidence_score=0.0,
                corroboration_count=1,
            )
            db.add(incident)
            db.flush()  # Generate incident.id before report association
            is_independent = True

        report = EmergencyReport(
            user_id=user.id,
            incident_id=incident.id,
            emergency_type=report_data.emergency_type,
            description=report_data.description,
            severity=report_data.severity,
            latitude=report_data.latitude,
            longitude=report_data.longitude,
            is_independent=is_independent,
            confidence_contribution=0.0,
            photo_url=photo_url,
        )
        db.add(report)
        db.flush()  # Save report association so incident.reports is populated

        # Recalculate deterministic incident confidence score and preliminary status
        incident.confidence_score = calculate_incident_confidence(db, incident)
        update_incident_status_from_confidence(incident, db=db)

        db.commit()

        db.refresh(report)
        db.refresh(incident)
        return report, incident

    except Exception:
        db.rollback()
        raise


def get_report_by_id(db: Session, report_id: str) -> EmergencyReport | None:
    """Retrieve an emergency report by primary key ID."""
    return db.get(EmergencyReport, report_id)


def get_active_incidents(
    db: Session,
    emergency_type: EmergencyType | None = None,
    severity: SeverityLevel | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_meters: float | None = None,
) -> list[Incident]:
    """Retrieve active incidents (excluding RESOLVED and FALSE_ALARM) with optional filters."""
    statement = select(Incident).where(
        Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.FALSE_ALARM])
    )

    if emergency_type is not None:
        statement = statement.where(Incident.emergency_type == emergency_type)
    if severity is not None:
        statement = statement.where(Incident.severity == severity)

    statement = statement.order_by(Incident.created_at.desc())
    incidents = list(db.scalars(statement).all())

    # Spatial radius filtering in application layer if coordinates and radius provided
    if latitude is not None and longitude is not None and radius_meters is not None:
        incidents = [
            inc
            for inc in incidents
            if is_within_radius(
                inc.latitude, inc.longitude, latitude, longitude, radius_meters
            )
        ]

    return incidents


def get_incident_by_id(db: Session, incident_id: str) -> Incident | None:
    """Retrieve an incident by primary key ID."""
    return db.get(Incident, incident_id)
