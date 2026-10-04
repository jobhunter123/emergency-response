"""Tests for SQLAlchemy database models, relationships, defaults, and schemas."""

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    EmergencyReport,
    EmergencyType,
    Incident,
    IncidentStatus,
    SeverityLevel,
    User,
)
from app.schemas import (
    EmergencyReportCreate,
    EmergencyReportResponse,
    IncidentResponse,
    UserCreate,
    UserResponse,
)


@pytest.fixture
def db_session() -> Session:
    """Provide an isolated, in-memory SQLite database session for tests."""
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


def test_create_user(db_session: Session) -> None:
    """Test that a User record can be created with expected defaults."""
    user = User(
        email="citizen1@example.com",
        hashed_password="hashed_secret_value",
        full_name="Jane Doe",
        phone_number="+1234567890",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert len(user.id) == 36
    assert user.email == "citizen1@example.com"
    assert user.is_active is True
    assert user.is_responder is False
    assert user.created_at is not None
    assert user.updated_at is not None


def test_create_incident_defaults(db_session: Session) -> None:
    """Test creating an Incident and verify all specified default values."""
    incident = Incident(
        emergency_type=EmergencyType.FIRE,
        title="Brush fire near park entrance",
        description="Visible smoke and flames near North Trailhead.",
        severity=SeverityLevel.HIGH,
        latitude=37.7749,
        longitude=-122.4194,
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    assert incident.id is not None
    assert incident.status == IncidentStatus.UNVERIFIED
    assert incident.confidence_score == 0.0
    assert incident.corroboration_count == 0
    assert incident.affected_radius_meters == 500.0
    assert incident.created_at is not None
    assert incident.updated_at is not None
    assert incident.confirmed_at is None


def test_create_emergency_report(db_session: Session) -> None:
    """Test creating an EmergencyReport referencing a User."""
    user = User(
        email="reporter@example.com",
        hashed_password="hashed_password",
    )
    db_session.add(user)
    db_session.commit()

    report = EmergencyReport(
        user_id=user.id,
        emergency_type=EmergencyType.ACCIDENT,
        description="Two-car collision blocking right lane.",
        severity=SeverityLevel.MEDIUM,
        latitude=37.7833,
        longitude=-122.4167,
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)

    assert report.id is not None
    assert report.user_id == user.id
    assert report.incident_id is None
    assert report.confidence_contribution == 0.0
    assert report.is_independent is True
    assert report.reported_at is not None


def test_emergency_report_references_user_and_incident(
    db_session: Session,
) -> None:
    """Test that EmergencyReport correctly references both User and Incident."""
    user = User(
        email="witness@example.com",
        hashed_password="hashed_password",
    )
    incident = Incident(
        emergency_type=EmergencyType.FLOOD,
        title="Flash flooding on main avenue",
        severity=SeverityLevel.CRITICAL,
        latitude=37.7600,
        longitude=-122.4200,
    )
    db_session.add_all([user, incident])
    db_session.commit()

    report = EmergencyReport(
        user_id=user.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.FLOOD,
        description="Water level reaching vehicle door handles.",
        severity=SeverityLevel.CRITICAL,
        latitude=37.7605,
        longitude=-122.4205,
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)

    assert report.user == user
    assert report.incident == incident
    assert report.incident_id == incident.id


def test_user_reports_relationship(db_session: Session) -> None:
    """Test the User -> reports relationship."""
    user = User(
        email="active_user@example.com",
        hashed_password="hashed_password",
    )
    db_session.add(user)
    db_session.commit()

    report1 = EmergencyReport(
        user_id=user.id,
        emergency_type=EmergencyType.MEDICAL,
        description="Person collapsed on sidewalk, breathing.",
        severity=SeverityLevel.HIGH,
        latitude=37.7700,
        longitude=-122.4100,
    )
    report2 = EmergencyReport(
        user_id=user.id,
        emergency_type=EmergencyType.UNSAFE_SITUATION,
        description="Exposed downed power cable sparking on sidewalk.",
        severity=SeverityLevel.HIGH,
        latitude=37.7710,
        longitude=-122.4110,
    )
    db_session.add_all([report1, report2])
    db_session.commit()
    db_session.refresh(user)

    assert len(user.reports) == 2
    report_ids = {r.id for r in user.reports}
    assert report1.id in report_ids
    assert report2.id in report_ids


def test_incident_reports_relationship(db_session: Session) -> None:
    """Test the Incident -> reports relationship with multiple corroborating reports."""
    incident = Incident(
        emergency_type=EmergencyType.EARTHQUAKE,
        title="Earthquake tremor structural damage",
        severity=SeverityLevel.CRITICAL,
        latitude=37.7749,
        longitude=-122.4194,
    )
    user_a = User(email="user_a@example.com", hashed_password="pw1")
    user_b = User(email="user_b@example.com", hashed_password="pw2")
    user_c = User(email="user_c@example.com", hashed_password="pw3")
    db_session.add_all([incident, user_a, user_b, user_c])
    db_session.commit()

    report_a = EmergencyReport(
        user_id=user_a.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.EARTHQUAKE,
        description="Felt strong tremor, cracked wall in lobby.",
        severity=SeverityLevel.HIGH,
        latitude=37.7750,
        longitude=-122.4190,
    )
    report_b = EmergencyReport(
        user_id=user_b.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.EARTHQUAKE,
        description="Broken window glass falling onto sidewalk.",
        severity=SeverityLevel.CRITICAL,
        latitude=37.7748,
        longitude=-122.4195,
    )
    report_c = EmergencyReport(
        user_id=user_c.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.EARTHQUAKE,
        description="Power outage and gas smell on 4th street.",
        severity=SeverityLevel.HIGH,
        latitude=37.7747,
        longitude=-122.4196,
    )
    db_session.add_all([report_a, report_b, report_c])
    db_session.commit()
    db_session.refresh(incident)

    assert len(incident.reports) == 3
    assert {r.user_id for r in incident.reports} == {
        user_a.id,
        user_b.id,
        user_c.id,
    }


def test_enums_store_and_load_correctly(db_session: Session) -> None:
    """Test that string-based enums correctly serialize and deserialize."""
    incident = Incident(
        emergency_type=EmergencyType.LANDSLIDE,
        title="Landslide on mountain pass road",
        severity=SeverityLevel.CRITICAL,
        status=IncidentStatus.CONFIRMED,
        latitude=37.8000,
        longitude=-122.4000,
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    assert incident.emergency_type == EmergencyType.LANDSLIDE
    assert incident.severity == SeverityLevel.CRITICAL
    assert incident.status == IncidentStatus.CONFIRMED


def test_pydantic_schemas_serialization(db_session: Session) -> None:
    """Test Pydantic schemas correctly serialize ORM model instances."""
    user = User(
        email="schema_test@example.com",
        hashed_password="secret_hashed_password",
        full_name="Alex Smith",
        phone_number="+15550001111",
    )
    incident = Incident(
        emergency_type=EmergencyType.STORM,
        title="Severe hail storm",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.VERIFYING,
        latitude=37.7749,
        longitude=-122.4194,
        confidence_score=45.5,
        corroboration_count=2,
    )
    db_session.add_all([user, incident])
    db_session.commit()

    report = EmergencyReport(
        user_id=user.id,
        incident_id=incident.id,
        emergency_type=EmergencyType.STORM,
        description="Golf ball sized hail damaging car windshields.",
        severity=SeverityLevel.HIGH,
        latitude=37.7749,
        longitude=-122.4194,
        confidence_contribution=22.5,
    )
    db_session.add(report)
    db_session.commit()

    # User response validation (ensuring hashed_password is NOT present)
    user_dto = UserResponse.model_validate(user)
    assert user_dto.id == user.id
    assert user_dto.email == "schema_test@example.com"
    assert not hasattr(user_dto, "hashed_password")

    # Incident response validation
    incident_dto = IncidentResponse.model_validate(incident)
    assert incident_dto.id == incident.id
    assert incident_dto.confidence_score == 45.5
    assert incident_dto.corroboration_count == 2
    assert incident_dto.status == IncidentStatus.VERIFYING

    # Emergency report response validation
    report_dto = EmergencyReportResponse.model_validate(report)
    assert report_dto.id == report.id
    assert report_dto.user_id == user.id
    assert report_dto.incident_id == incident.id
    assert report_dto.confidence_contribution == 22.5


def test_schema_validations() -> None:
    """Test Pydantic input validation for email and geographic bounds."""
    # Invalid email
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="validpassword123")

    # Invalid latitude (> 90)
    with pytest.raises(ValidationError):
        EmergencyReportCreate(
            emergency_type=EmergencyType.FIRE,
            description="Out of bounds fire coordinates",
            severity=SeverityLevel.MEDIUM,
            latitude=95.0,
            longitude=-122.4,
        )

    # Invalid longitude (< -180)
    with pytest.raises(ValidationError):
        EmergencyReportCreate(
            emergency_type=EmergencyType.FIRE,
            description="Out of bounds fire coordinates",
            severity=SeverityLevel.MEDIUM,
            latitude=37.7,
            longitude=-195.0,
        )
