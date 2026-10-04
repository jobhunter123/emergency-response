"""Comprehensive tests for Alert model, alert creation service, and alert APIs."""

from collections.abc import Generator
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.alert import Alert
from app.models.enums import EmergencyType, IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.user import User
from app.services.alerts import (
    create_incident_alerts,
    get_user_alerts,
    mark_alert_as_read,
)
from app.services.incident_status import update_incident_status


@pytest.fixture
def test_session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory SQLite database session for alert tests."""
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
def client(test_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency."""

    def override_get_db() -> Generator[Session, None, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(
    session: Session,
    email: str,
    lat: float | None = None,
    lon: float | None = None,
    is_active: bool = True,
    is_responder: bool = False,
) -> User:
    """Helper to create and persist a test user."""
    user = User(
        email=email,
        hashed_password="hashed_test_password",
        full_name=f"User {email}",
        is_active=is_active,
        is_responder=is_responder,
        latitude=lat,
        longitude=lon,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def make_incident(
    session: Session,
    status: IncidentStatus = IncidentStatus.UNVERIFIED,
    radius: float = 500.0,
    lat: float = 22.5726,
    lon: float = 88.3639,
) -> Incident:
    """Helper to create and persist a test incident."""
    incident = Incident(
        emergency_type=EmergencyType.FIRE,
        title="Warehouse Fire",
        description="Heavy smoke billowing from rooftop",
        severity=SeverityLevel.HIGH,
        status=status,
        latitude=lat,
        longitude=lon,
        affected_radius_meters=radius,
        confidence_score=40.0,
    )
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


def test_alert_table_and_model_creation(test_session: Session) -> None:
    """Test that Alert records can be created, persisted, and queried."""
    user = make_user(test_session, "alert_model@example.com", 22.5726, 88.3639)
    incident = make_incident(test_session, IncidentStatus.CONFIRMED)

    alert = Alert(
        incident_id=incident.id,
        user_id=user.id,
        title="Emergency Alert: Fire",
        message="A confirmed fire has been reported near your location.",
        severity=SeverityLevel.HIGH,
    )
    test_session.add(alert)
    test_session.commit()
    test_session.refresh(alert)

    assert alert.id is not None
    assert len(alert.id) == 36
    assert alert.is_read is False
    assert alert.read_at is None
    assert alert.incident.id == incident.id
    assert alert.user.id == user.id


def test_confirmed_incident_creates_alerts_for_affected_active_users(
    test_session: Session,
) -> None:
    """Test that create_incident_alerts alerts active users within radius and skips distant/inactive ones."""
    # Incident at (22.5726, 88.3639) with 500m radius
    incident = make_incident(test_session, IncidentStatus.CONFIRMED, radius=500.0)

    # User A: Active, nearby (22.5730, 88.3639) -> ~44m
    user_a = make_user(test_session, "user_a@example.com", 22.5730, 88.3639, is_active=True)
    # User B: Active, distant (22.5900, 88.3900) -> ~3.3km
    user_b = make_user(test_session, "user_b@example.com", 22.5900, 88.3900, is_active=True)
    # User C: Inactive, nearby (22.5728, 88.3639)
    user_c = make_user(test_session, "user_c@example.com", 22.5728, 88.3639, is_active=False)

    created_alerts = create_incident_alerts(test_session, incident)

    assert len(created_alerts) == 1
    assert created_alerts[0].user_id == user_a.id
    assert created_alerts[0].incident_id == incident.id
    assert "Fire" in created_alerts[0].title


def test_user_outside_radius_does_not_receive_alert(test_session: Session) -> None:
    """Test that users outside the affected radius do not receive alerts."""
    incident = make_incident(test_session, IncidentStatus.CONFIRMED, radius=300.0)
    user_distant = make_user(test_session, "outside@example.com", 22.5900, 88.3900)

    alerts = create_incident_alerts(test_session, incident)
    assert len(alerts) == 0

    user_alerts = get_user_alerts(test_session, user_distant.id)
    assert len(user_alerts) == 0


def test_inactive_user_does_not_receive_alert(test_session: Session) -> None:
    """Test that inactive users inside radius do not receive alerts."""
    incident = make_incident(test_session, IncidentStatus.CONFIRMED, radius=500.0)
    user_inactive = make_user(
        test_session, "inactive_close@example.com", 22.5728, 88.3639, is_active=False
    )

    alerts = create_incident_alerts(test_session, incident)
    assert len(alerts) == 0
    assert len(get_user_alerts(test_session, user_inactive.id)) == 0


def test_duplicate_alert_is_not_created(test_session: Session) -> None:
    """Test that repeated calls to create_incident_alerts do not create duplicate records."""
    incident = make_incident(test_session, IncidentStatus.CONFIRMED, radius=500.0)
    user = make_user(test_session, "dedup@example.com", 22.5727, 88.3639)

    first_call = create_incident_alerts(test_session, incident)
    assert len(first_call) == 1

    second_call = create_incident_alerts(test_session, incident)
    assert len(second_call) == 0

    user_alerts = get_user_alerts(test_session, user.id)
    assert len(user_alerts) == 1


def test_unverified_and_verifying_do_not_generate_alerts(test_session: Session) -> None:
    """Test that UNVERIFIED and VERIFYING incidents never generate alerts."""
    user = make_user(test_session, "unverified_test@example.com", 22.5726, 88.3639)

    inc_unverified = make_incident(test_session, IncidentStatus.UNVERIFIED)
    alerts_unv = create_incident_alerts(test_session, inc_unverified)
    assert len(alerts_unv) == 0

    inc_verifying = make_incident(test_session, IncidentStatus.VERIFYING)
    alerts_ver = create_incident_alerts(test_session, inc_verifying)
    assert len(alerts_ver) == 0


def test_responder_transition_to_confirmed_creates_alerts(test_session: Session) -> None:
    """Test that updating status to CONFIRMED automatically triggers alert creation."""
    responder = make_user(
        test_session, "responder1@example.com", is_responder=True
    )
    affected_citizen = make_user(
        test_session, "citizen1@example.com", 22.5728, 88.3639
    )

    incident = make_incident(test_session, IncidentStatus.VERIFYING)

    updated_inc = update_incident_status(
        db=test_session,
        incident=incident,
        new_status=IncidentStatus.CONFIRMED,
        responder=responder,
    )
    assert updated_inc.status == IncidentStatus.CONFIRMED

    alerts = get_user_alerts(test_session, affected_citizen.id)
    assert len(alerts) == 1
    assert alerts[0].incident_id == incident.id


def test_confirmed_to_responding_does_not_duplicate_alerts(test_session: Session) -> None:
    """Test that advancing from CONFIRMED to RESPONDING does not create duplicate alerts."""
    responder = make_user(
        test_session, "responder2@example.com", is_responder=True
    )
    affected_citizen = make_user(
        test_session, "citizen2@example.com", 22.5728, 88.3639
    )

    incident = make_incident(test_session, IncidentStatus.VERIFYING)

    # VERIFYING -> CONFIRMED
    update_incident_status(
        db=test_session,
        incident=incident,
        new_status=IncidentStatus.CONFIRMED,
        responder=responder,
    )
    assert len(get_user_alerts(test_session, affected_citizen.id)) == 1

    # CONFIRMED -> RESPONDING
    update_incident_status(
        db=test_session,
        incident=incident,
        new_status=IncidentStatus.RESPONDING,
        responder=responder,
    )
    alerts_after_responding = get_user_alerts(test_session, affected_citizen.id)
    assert len(alerts_after_responding) == 1


def test_user_can_retrieve_own_alerts(client: TestClient, test_session: Session) -> None:
    """Test GET /api/v1/alerts returns alerts belonging to the authenticated user."""
    user = make_user(test_session, "reader@example.com", 22.5726, 88.3639)
    incident = make_incident(test_session, IncidentStatus.CONFIRMED)

    alert1 = Alert(
        incident_id=incident.id,
        user_id=user.id,
        title="Alert 1",
        message="First message",
        severity=SeverityLevel.HIGH,
    )
    alert2 = Alert(
        incident_id=incident.id,
        user_id=user.id,
        title="Alert 2",
        message="Second message",
        severity=SeverityLevel.CRITICAL,
    )
    test_session.add_all([alert1, alert2])
    test_session.commit()

    token = create_access_token(subject=user.id)
    response = client.get(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] in ("Alert 1", "Alert 2")


def test_user_cannot_retrieve_another_users_alerts(
    client: TestClient, test_session: Session
) -> None:
    """Test that users only see their own alerts and cannot see other users' alerts."""
    user_a = make_user(test_session, "user_alpha@example.com", 22.5726, 88.3639)
    user_b = make_user(test_session, "user_beta@example.com", 22.5726, 88.3639)
    incident = make_incident(test_session, IncidentStatus.CONFIRMED)

    alert_b = Alert(
        incident_id=incident.id,
        user_id=user_b.id,
        title="Alert for Beta",
        message="Beta only",
        severity=SeverityLevel.MEDIUM,
    )
    test_session.add(alert_b)
    test_session.commit()

    # User A requests alerts
    token_a = create_access_token(subject=user_a.id)
    response = client.get(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_unread_only_query_param(client: TestClient, test_session: Session) -> None:
    """Test GET /api/v1/alerts?unread_only=true returns only unread alerts."""
    user = make_user(test_session, "unread_tester@example.com", 22.5726, 88.3639)
    incident = make_incident(test_session, IncidentStatus.CONFIRMED)

    read_alert = Alert(
        incident_id=incident.id,
        user_id=user.id,
        title="Old Read Alert",
        message="Already viewed",
        severity=SeverityLevel.LOW,
        is_read=True,
        read_at=datetime.utcnow(),
    )
    unread_alert = Alert(
        incident_id=incident.id,
        user_id=user.id,
        title="Fresh Unread Alert",
        message="Needs attention",
        severity=SeverityLevel.HIGH,
        is_read=False,
    )
    test_session.add_all([read_alert, unread_alert])
    test_session.commit()

    token = create_access_token(subject=user.id)
    # Default returns all
    resp_all = client.get(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_all.status_code == 200
    assert len(resp_all.json()) == 2

    # unread_only=true returns only unread
    resp_unread = client.get(
        "/api/v1/alerts?unread_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_unread.status_code == 200
    unread_data = resp_unread.json()
    assert len(unread_data) == 1
    assert unread_data[0]["title"] == "Fresh Unread Alert"
    assert unread_data[0]["is_read"] is False


def test_user_can_mark_own_alert_as_read(client: TestClient, test_session: Session) -> None:
    """Test PATCH /api/v1/alerts/{alert_id}/read updates is_read and read_at."""
    user = make_user(test_session, "mark_read@example.com", 22.5726, 88.3639)
    incident = make_incident(test_session, IncidentStatus.CONFIRMED)

    alert = Alert(
        incident_id=incident.id,
        user_id=user.id,
        title="Unread Alert",
        message="Important info",
        severity=SeverityLevel.HIGH,
        is_read=False,
    )
    test_session.add(alert)
    test_session.commit()
    test_session.refresh(alert)

    token = create_access_token(subject=user.id)
    response = client.patch(
        f"/api/v1/alerts/{alert.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_read"] is True
    assert data["read_at"] is not None

    # Verify DB state
    test_session.refresh(alert)
    assert alert.is_read is True
    assert alert.read_at is not None


def test_another_user_cannot_mark_alert_as_read(
    client: TestClient, test_session: Session
) -> None:
    """Test PATCH /api/v1/alerts/{alert_id}/read rejects another user with 403."""
    user_owner = make_user(test_session, "owner@example.com")
    user_intruder = make_user(test_session, "intruder@example.com")
    incident = make_incident(test_session, IncidentStatus.CONFIRMED)

    alert = Alert(
        incident_id=incident.id,
        user_id=user_owner.id,
        title="Owner Alert",
        message="Private alert",
        severity=SeverityLevel.HIGH,
        is_read=False,
    )
    test_session.add(alert)
    test_session.commit()
    test_session.refresh(alert)

    token_intruder = create_access_token(subject=user_intruder.id)
    response = client.patch(
        f"/api/v1/alerts/{alert.id}/read",
        headers={"Authorization": f"Bearer {token_intruder}"},
    )
    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


def test_mark_nonexistent_alert_as_read(client: TestClient, test_session: Session) -> None:
    """Test PATCH /api/v1/alerts/{alert_id}/read with nonexistent id returns 404."""
    user = make_user(test_session, "nonexistent_tester@example.com")
    token = create_access_token(subject=user.id)

    response = client.patch(
        "/api/v1/alerts/nonexistent-alert-id/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_unauthenticated_cannot_access_alerts(client: TestClient) -> None:
    """Test unauthenticated calls to alerts endpoints return 401."""
    assert client.get("/api/v1/alerts").status_code == 401
    assert client.patch("/api/v1/alerts/any-id/read").status_code == 401


def test_user_location_update_endpoint(client: TestClient, test_session: Session) -> None:
    """Test PATCH /api/v1/users/me/location updates snapshot and validates coordinates."""
    user = make_user(test_session, "loc_updater@example.com")
    token = create_access_token(subject=user.id)

    # Valid coordinates
    payload = {"latitude": 22.5726, "longitude": 88.3639}
    resp = client.patch(
        "/api/v1/users/me/location",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["latitude"] == 22.5726
    assert data["longitude"] == 88.3639
    assert data["location_updated_at"] is not None

    # Invalid latitude > 90
    resp_invalid_lat = client.patch(
        "/api/v1/users/me/location",
        json={"latitude": 95.0, "longitude": 88.3639},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_invalid_lat.status_code == 422

    # Invalid longitude < -180
    resp_invalid_lon = client.patch(
        "/api/v1/users/me/location",
        json={"latitude": 22.5726, "longitude": -185.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_invalid_lon.status_code == 422


def test_incident_detail_exposes_affected_area_and_count(
    client: TestClient, test_session: Session
) -> None:
    """Test that GET /api/v1/incidents/{incident_id} exposes affected_area and affected_user_count."""
    # Create incident
    incident = make_incident(test_session, IncidentStatus.CONFIRMED, radius=500.0)

    # User nearby inside radius
    make_user(test_session, "in_radius@example.com", 22.5730, 88.3639)
    # User outside radius
    make_user(test_session, "out_radius@example.com", 22.5900, 88.3900)

    resp = client.get(f"/api/v1/incidents/{incident.id}")
    assert resp.status_code == 200
    data = resp.json()

    assert "affected_area" in data
    area = data["affected_area"]
    assert area["center"]["latitude"] == incident.latitude
    assert area["center"]["longitude"] == incident.longitude
    assert area["radius_meters"] == incident.affected_radius_meters
    assert "bounds" in area

    assert "affected_user_count" in data
    assert data["affected_user_count"] == 1
