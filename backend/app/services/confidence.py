"""Deterministic confidence and corroboration scoring engine for emergency incidents.

Domain Principles:
1. Confidence is a dynamic score indicating corroboration strength across independent reports.
2. It represents the platform's current corroboration signal, NOT absolute ground truth.
3. Official confirmation remains a separate responder/admin action.
"""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.emergency_report import EmergencyReport
from app.models.enums import IncidentStatus
from app.models.incident import Incident
from app.services.geolocation import calculate_distance_meters

# Maximum score thresholds by component
MAX_BASE_CORROBORATION: float = 75.0
MAX_GEOGRAPHIC_BONUS: float = 15.0
MAX_TEMPORAL_BONUS: float = 10.0
MAX_SEVERITY_BONUS: float = 5.0


def calculate_geographic_bonus(
    incident: Incident, reports: list[EmergencyReport]
) -> float:
    """Calculate proximity bonus of independent reports to the incident center (max 15.0).

    Tiers (relative to incident.affected_radius_meters):
    - Within 25% of radius: +15
    - Within 50% of radius: +10
    - Within 100% of radius: +5
    - Outside radius: +0
    """
    if not reports:
        return 0.0

    radius = (
        incident.affected_radius_meters
        if incident.affected_radius_meters > 0.0
        else 500.0
    )
    bonuses: list[float] = []

    for report in reports:
        dist = calculate_distance_meters(
            report.latitude, report.longitude, incident.latitude, incident.longitude
        )
        if dist <= 0.25 * radius:
            bonuses.append(15.0)
        elif dist <= 0.50 * radius:
            bonuses.append(10.0)
        elif dist <= 1.0 * radius:
            bonuses.append(5.0)
        else:
            bonuses.append(0.0)

    avg_bonus = sum(bonuses) / len(bonuses)
    return min(MAX_GEOGRAPHIC_BONUS, max(0.0, avg_bonus))


def calculate_temporal_bonus(
    reports: list[EmergencyReport], evaluation_time: datetime | None = None
) -> float:
    """Calculate recency bonus across independent reports relative to evaluation time (max 10.0).

    Tiers:
    - <= 5 minutes: +10
    - <= 15 minutes: +8
    - <= 30 minutes: +5
    - <= 60 minutes: +2
    - > 60 minutes: +0
    """
    if not reports:
        return 0.0

    now = evaluation_time or datetime.now(timezone.utc)
    bonuses: list[float] = []

    for report in reports:
        reported_at = report.reported_at
        if reported_at.tzinfo is None:
            reported_at = reported_at.replace(tzinfo=timezone.utc)

        age_seconds = (now - reported_at).total_seconds()
        age_minutes = max(0.0, age_seconds / 60.0)

        if age_minutes <= 5.0:
            bonuses.append(10.0)
        elif age_minutes <= 15.0:
            bonuses.append(8.0)
        elif age_minutes <= 30.0:
            bonuses.append(5.0)
        elif age_minutes <= 60.0:
            bonuses.append(2.0)
        else:
            bonuses.append(0.0)

    avg_bonus = sum(bonuses) / len(bonuses)
    return min(MAX_TEMPORAL_BONUS, max(0.0, avg_bonus))


def calculate_severity_bonus(
    incident: Incident, reports: list[EmergencyReport]
) -> float:
    """Calculate consistency bonus based on report agreement with incident severity (max 5.0).

    Tiers:
    - Agreement ratio >= 75%: +5
    - Agreement ratio >= 50%: +3
    - Agreement ratio > 0%: +1
    - Agreement ratio == 0%: +0
    """
    if not reports:
        return 0.0

    matching_count = sum(1 for r in reports if r.severity == incident.severity)
    ratio = matching_count / len(reports)

    if ratio >= 0.75:
        return 5.0
    elif ratio >= 0.50:
        return 3.0
    elif ratio > 0.0:
        return 1.0
    else:
        return 0.0


def calculate_incident_confidence(
    db: Session | None,
    incident: Incident,
    evaluation_time: datetime | None = None,
) -> float:
    """Calculate the deterministic confidence score (0.0 to 100.0) for an incident.

    Formula:
    confidence = base_corroboration + geographic_bonus + temporal_bonus + severity_bonus

    Independent corroboration schedule:
    - 0 independent reports: 0
    - 1 independent report: 25
    - 2 independent reports: 45
    - 3 independent reports: 60
    - 4 independent reports: 70
    - 5+ independent reports: 75
    """
    # If a database session is provided, query directly to reflect flushed changes
    if db is not None and incident.id is not None:
        statement = select(EmergencyReport).where(
            EmergencyReport.incident_id == incident.id,
            EmergencyReport.is_independent == True,  # noqa: E712
        )
        independent_reports = list(db.scalars(statement).all())
    else:
        independent_reports = [r for r in incident.reports if r.is_independent]

    count = len(independent_reports)

    if count <= 0:
        return 0.0
    elif count == 1:
        base_score = 25.0
    elif count == 2:
        base_score = 45.0
    elif count == 3:
        base_score = 60.0
    elif count == 4:
        base_score = 70.0
    else:
        base_score = 75.0

    geo_bonus = calculate_geographic_bonus(incident, independent_reports)
    temp_bonus = calculate_temporal_bonus(independent_reports, evaluation_time)
    sev_bonus = calculate_severity_bonus(incident, independent_reports)

    raw_score = base_score + geo_bonus + temp_bonus + sev_bonus
    clamped_score = min(100.0, max(0.0, raw_score))
    return round(clamped_score, 1)


def get_confidence_level(score: float) -> str:
    """Convert numeric confidence score (0-100) into a human-readable category.

    Tiers:
    - 0 to 24.9: LOW
    - 25 to 49.9: MODERATE
    - 50 to 74.9: HIGH
    - 75 to 100: VERY_HIGH
    """
    if score < 25.0:
        return "LOW"
    elif score < 50.0:
        return "MODERATE"
    elif score < 75.0:
        return "HIGH"
    else:
        return "VERY_HIGH"


def update_incident_status_from_confidence(
    incident: Incident, db: Session | None = None
) -> None:
    """Apply preliminary status transitions based on confidence and corroboration.

    Transitions:
    - score < 25: status remains UNVERIFIED
    - score >= 25 with 2+ independent reports: status transitions to VERIFYING
    - Single reports remain UNVERIFIED because one report cannot corroborate itself.
    - Does NOT automatically transition to CONFIRMED (requires official responder action).
    """
    if incident.status == IncidentStatus.UNVERIFIED:
        if db is not None and incident.id is not None:
            statement = select(EmergencyReport).where(
                EmergencyReport.incident_id == incident.id,
                EmergencyReport.is_independent == True,  # noqa: E712
            )
            count = len(list(db.scalars(statement).all()))
        else:
            count = sum(1 for r in incident.reports if r.is_independent)

        if incident.confidence_score >= 25.0 and count >= 2:
            incident.status = IncidentStatus.VERIFYING
