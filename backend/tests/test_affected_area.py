"""Tests for affected area spatial calculations and affected user discovery."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.enums import EmergencyType, IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.user import User
from app.services.affected_area import (
    calculate_affected_area,
    count_affected_users,
    find_affected_users,
    is_location_affected,
)


@pytest.fixture
def db_session() -> Session:
    """Provide an isolated, in-memory SQLite database session."""
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


@pytest.fixture
def sample_incident() -> Incident:
    """Create a sample incident with 500m radius centered at (22.5726, 88.3639)."""
    return Incident(
        id="inc-test-001",
        emergency_type=EmergencyType.FIRE,
        title="Fire incident",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.CONFIRMED,
        latitude=22.5726,
        longitude=88.3639,
        affected_radius_meters=500.0,
    )


def test_location_inside_radius_is_affected(sample_incident: Incident) -> None:
    """Test that a coordinate pair well within 500m is deemed affected."""
    # (22.5730, 88.3639) is approx 44 meters north
    assert is_location_affected(22.5730, 88.3639, sample_incident) is True


def test_location_outside_radius_is_not_affected(sample_incident: Incident) -> None:
    """Test that a coordinate pair far outside the 500m radius is not affected."""
    # (22.5900, 88.3900) is ~3.3 km away
    assert is_location_affected(22.5900, 88.3900, sample_incident) is False


def test_boundary_behavior(sample_incident: Incident) -> None:
    """Test behavior right at and slightly beyond the 500m boundary."""
    # Exact center is affected
    assert is_location_affected(22.5726, 88.3639, sample_incident) is True

    # 1 degree lat is ~111,320m. 500m is ~0.0044915 deg.
    # At +0.0040 degrees (~445m): within radius
    assert is_location_affected(22.5766, 88.3639, sample_incident) is True
    # At +0.0060 degrees (~667m): outside radius
    assert is_location_affected(22.5786, 88.3639, sample_incident) is False


def test_affected_area_center_and_radius(sample_incident: Incident) -> None:
    """Test that calculate_affected_area matches incident center and radius."""
    area = calculate_affected_area(sample_incident)
    assert area["center"]["latitude"] == sample_incident.latitude
    assert area["center"]["longitude"] == sample_incident.longitude
    assert area["radius_meters"] == sample_incident.affected_radius_meters
    assert "bounds" in area
    bounds = area["bounds"]
    assert bounds["north"] > sample_incident.latitude
    assert bounds["south"] < sample_incident.latitude
    assert bounds["east"] > sample_incident.longitude
    assert bounds["west"] < sample_incident.longitude


def test_find_and_count_affected_users(
    db_session: Session, sample_incident: Incident
) -> None:
    """Test discovery of active users within the affected radius."""
    db_session.add(sample_incident)

    # User 1: Active, within radius (44m away)
    user_nearby = User(
        email="nearby@example.com",
        hashed_password="pw",
        is_active=True,
        latitude=22.5730,
        longitude=88.3639,
    )
    # User 2: Active, far away (~3.3km)
    user_distant = User(
        email="distant@example.com",
        hashed_password="pw",
        is_active=True,
        latitude=22.5900,
        longitude=88.3900,
    )
    # User 3: Inactive, inside radius
    user_inactive = User(
        email="inactive@example.com",
        hashed_password="pw",
        is_active=False,
        latitude=22.5728,
        longitude=88.3639,
    )
    # User 4: Active, no location set
    user_no_loc = User(
        email="noloc@example.com",
        hashed_password="pw",
        is_active=True,
        latitude=None,
        longitude=None,
    )

    db_session.add_all([user_nearby, user_distant, user_inactive, user_no_loc])
    db_session.commit()

    affected = find_affected_users(db_session, sample_incident)
    assert len(affected) == 1
    assert affected[0].id == user_nearby.id

    count = count_affected_users(db_session, sample_incident)
    assert count == 1
