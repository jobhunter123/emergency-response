"""Tests for the deterministic confidence/corroboration scoring engine."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.emergency_report import EmergencyReport
from app.models.enums import EmergencyType, IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.user import User
from app.services.confidence import (
    calculate_geographic_bonus,
    calculate_incident_confidence,
    calculate_severity_bonus,
    calculate_temporal_bonus,
    get_confidence_level,
    update_incident_status_from_confidence,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory SQLite session for confidence engine tests."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


def test_single_independent_report_produces_valid_nonzero_score(
    db_session: Session,
) -> None:
    """1. One independent report produces a valid non-zero confidence score."""
    user = User(email="u1@example.com", hashed_password="pw")
    incident = Incident(
        emergency_type=EmergencyType.FIRE,
        title="Fire",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.UNVERIFIED,
        latitude=22.5726,
        longitude=88.3639,
        affected_radius_meters=500.0,
    )
    db_session.add_all([user, incident])
    db_session.flush()

    report = EmergencyReport(
        user_id=user.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.FIRE,
        description="Fire observed",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        is_independent=True,
    )
    db_session.add(report)
    db_session.flush()

    score = calculate_incident_confidence(db_session, incident)
    assert score > 0.0
    # Expected: 25 (base) + 15 (geo <= 25%) + 10 (temp <= 5m) + 5 (sev agree) = 55.0
    assert score == 55.0


def test_two_independent_reports_produce_higher_confidence(
    db_session: Session,
) -> None:
    """2. Two independent nearby reports produce higher confidence than one."""
    user1 = User(email="u1@example.com", hashed_password="pw")
    user2 = User(email="u2@example.com", hashed_password="pw")
    incident = Incident(
        emergency_type=EmergencyType.FLOOD,
        title="Flood",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        affected_radius_meters=500.0,
    )
    db_session.add_all([user1, user2, incident])
    db_session.flush()

    report1 = EmergencyReport(
        user_id=user1.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.FLOOD,
        description="High water",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        is_independent=True,
    )
    db_session.add(report1)
    db_session.flush()
    score_1 = calculate_incident_confidence(db_session, incident)

    report2 = EmergencyReport(
        user_id=user2.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.FLOOD,
        description="Road submerged",
        severity=SeverityLevel.HIGH,
        latitude=22.5730,
        longitude=88.3640,
        is_independent=True,
    )
    db_session.add(report2)
    db_session.flush()
    score_2 = calculate_incident_confidence(db_session, incident)

    assert score_2 > score_1


def test_three_independent_reports_produce_higher_confidence_than_two(
    db_session: Session,
) -> None:
    """3. Three independent reports produce higher confidence than two."""
    users = [User(email=f"u{i}@example.com", hashed_password="pw") for i in range(3)]
    incident = Incident(
        emergency_type=EmergencyType.ACCIDENT,
        title="Accident",
        severity=SeverityLevel.MEDIUM,
        latitude=22.5726,
        longitude=88.3639,
        affected_radius_meters=500.0,
    )
    db_session.add_all(users + [incident])
    db_session.flush()

    for i in range(2):
        db_session.add(
            EmergencyReport(
                user_id=users[i].id,
                incident_id=incident.id,
                emergency_type=EmergencyType.ACCIDENT,
                description=f"Accident {i}",
                severity=SeverityLevel.MEDIUM,
                latitude=22.5726,
                longitude=88.3639,
                is_independent=True,
            )
        )
    db_session.flush()
    score_2 = calculate_incident_confidence(db_session, incident)

    # Add third independent report
    db_session.add(
        EmergencyReport(
            user_id=users[2].id,
            incident_id=incident.id,
            emergency_type=EmergencyType.ACCIDENT,
            description="Accident 3",
            severity=SeverityLevel.MEDIUM,
            latitude=22.5726,
            longitude=88.3639,
            is_independent=True,
        )
    )
    db_session.flush()
    score_3 = calculate_incident_confidence(db_session, incident)

    assert score_3 > score_2


def test_duplicate_non_independent_reports_do_not_increase_confidence(
    db_session: Session,
) -> None:
    """4. Same-user duplicate/non-independent reports do not increase corroboration contribution."""
    user = User(email="u1@example.com", hashed_password="pw")
    incident = Incident(
        emergency_type=EmergencyType.FIRE,
        title="Fire",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        affected_radius_meters=500.0,
    )
    db_session.add_all([user, incident])
    db_session.flush()

    rep1 = EmergencyReport(
        user_id=user.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.FIRE,
        description="First observation",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        is_independent=True,
    )
    db_session.add(rep1)
    db_session.flush()
    score_before = calculate_incident_confidence(db_session, incident)

    # Same user submits duplicate report marked is_independent=False
    rep2 = EmergencyReport(
        user_id=user.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.FIRE,
        description="Duplicate observation",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        is_independent=False,
    )
    db_session.add(rep2)
    db_session.flush()
    score_after = calculate_incident_confidence(db_session, incident)

    assert score_after == score_before


def test_reports_outside_radius_do_not_receive_geographic_bonus() -> None:
    """5. Reports outside the incident radius do not receive geographic bonus."""
    incident = Incident(
        emergency_type=EmergencyType.FIRE,
        title="Fire",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        affected_radius_meters=500.0,
    )
    # Report at ~14km distance (22.68, 88.45)
    outside_report = EmergencyReport(
        user_id="u1",
        emergency_type=EmergencyType.FIRE,
        description="Distant report",
        severity=SeverityLevel.HIGH,
        latitude=22.6800,
        longitude=88.4500,
        is_independent=True,
    )
    bonus = calculate_geographic_bonus(incident, [outside_report])
    assert bonus == 0.0


def test_recent_reports_receive_higher_temporal_contribution() -> None:
    """6. Recent reports receive higher temporal contribution than older reports."""
    now = datetime.now(timezone.utc)

    recent_report = EmergencyReport(
        user_id="u1",
        emergency_type=EmergencyType.FIRE,
        description="Fresh",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        reported_at=now - timedelta(minutes=2),
    )
    old_report = EmergencyReport(
        user_id="u2",
        emergency_type=EmergencyType.FIRE,
        description="Stale",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        reported_at=now - timedelta(minutes=45),
    )

    recent_bonus = calculate_temporal_bonus([recent_report], evaluation_time=now)
    old_bonus = calculate_temporal_bonus([old_report], evaluation_time=now)

    assert recent_bonus == 10.0
    assert old_bonus == 2.0
    assert recent_bonus > old_bonus


def test_severity_agreement_contributes_positively() -> None:
    """7. Severity agreement contributes positively to confidence score."""
    incident = Incident(
        emergency_type=EmergencyType.STORM,
        title="Storm",
        severity=SeverityLevel.CRITICAL,
        latitude=22.5726,
        longitude=88.3639,
    )

    agreeing_report = EmergencyReport(
        user_id="u1",
        emergency_type=EmergencyType.STORM,
        description="Roof blown away",
        severity=SeverityLevel.CRITICAL,
        latitude=22.5726,
        longitude=88.3639,
    )
    disagreeing_report = EmergencyReport(
        user_id="u2",
        emergency_type=EmergencyType.STORM,
        description="Just light breeze",
        severity=SeverityLevel.LOW,
        latitude=22.5726,
        longitude=88.3639,
    )

    bonus_agree = calculate_severity_bonus(incident, [agreeing_report])
    bonus_disagree = calculate_severity_bonus(incident, [disagreeing_report])

    assert bonus_agree == 5.0
    assert bonus_disagree == 0.0


def test_final_score_clamped_between_0_and_100(db_session: Session) -> None:
    """8. Final score is always constrained between 0.0 and 100.0."""
    incident = Incident(
        emergency_type=EmergencyType.FIRE,
        title="Fire",
        severity=SeverityLevel.HIGH,
        latitude=22.5726,
        longitude=88.3639,
        affected_radius_meters=500.0,
    )
    db_session.add(incident)
    db_session.flush()

    # Empty reports -> 0
    assert calculate_incident_confidence(db_session, incident) == 0.0

    # 10 identical fresh reports (75 base + 15 geo + 10 temp + 5 sev = 105 -> clamped to 100.0)
    for i in range(10):
        db_session.add(
            EmergencyReport(
                user_id=f"u_{i}",
                incident_id=incident.id,
                emergency_type=EmergencyType.FIRE,
                description="Max score",
                severity=SeverityLevel.HIGH,
                latitude=22.5726,
                longitude=88.3639,
                is_independent=True,
            )
        )
    db_session.flush()
    score = calculate_incident_confidence(db_session, incident)
    assert score == 100.0
    assert 0.0 <= score <= 100.0


def test_confidence_level_boundaries() -> None:
    """9. Confidence level boundaries work as specified."""
    assert get_confidence_level(0.0) == "LOW"
    assert get_confidence_level(24.9) == "LOW"
    assert get_confidence_level(25.0) == "MODERATE"
    assert get_confidence_level(49.9) == "MODERATE"
    assert get_confidence_level(50.0) == "HIGH"
    assert get_confidence_level(74.9) == "HIGH"
    assert get_confidence_level(75.0) == "VERY_HIGH"
    assert get_confidence_level(100.0) == "VERY_HIGH"


def test_status_transitions_to_verifying_not_confirmed(db_session: Session) -> None:
    """10. Incident with sufficient corroboration becomes VERIFYING, NOT CONFIRMED."""
    users = [User(email=f"user_{i}@example.com", hashed_password="pw") for i in range(2)]
    incident = Incident(
        emergency_type=EmergencyType.LANDSLIDE,
        title="Landslide",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.UNVERIFIED,
        latitude=22.5726,
        longitude=88.3639,
        affected_radius_meters=500.0,
    )
    db_session.add_all(users + [incident])
    db_session.flush()

    # Add 2 independent reports
    for u in users:
        db_session.add(
            EmergencyReport(
                user_id=u.id,
                incident_id=incident.id,
                emergency_type=EmergencyType.LANDSLIDE,
                description="Rocks blocking highway",
                severity=SeverityLevel.HIGH,
                latitude=22.5726,
                longitude=88.3639,
                is_independent=True,
            )
        )
    db_session.flush()

    incident.confidence_score = calculate_incident_confidence(db_session, incident)
    assert incident.confidence_score >= 25.0
    update_incident_status_from_confidence(incident)

    # Status transitions to VERIFYING, never automatically CONFIRMED
    assert incident.status == IncidentStatus.VERIFYING
    assert incident.status != IncidentStatus.CONFIRMED
