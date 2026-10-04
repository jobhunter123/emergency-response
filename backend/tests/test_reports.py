"""Tests for emergency reporting endpoints, incident clustering, and spatial querying."""

from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import EmergencyType, IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.user import User


@pytest.fixture
def test_session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory SQLite database session for reporting tests."""
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


@pytest.fixture
def auth_headers_user1(test_session: Session) -> dict[str, str]:
    """Create test user 1 and return Authorization headers."""
    user = User(
        email="reporter1@example.com",
        hashed_password="pw",
        full_name="User One",
    )
    test_session.add(user)
    test_session.commit()
    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2(test_session: Session) -> dict[str, str]:
    """Create test user 2 and return Authorization headers."""
    user = User(
        email="reporter2@example.com",
        hashed_password="pw",
        full_name="User Two",
    )
    test_session.add(user)
    test_session.commit()
    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_cannot_create_report(client: TestClient) -> None:
    """Unauthenticated requests must be rejected with 401."""
    payload = {
        "emergency_type": "FIRE",
        "description": "Smoke in the alleyway",
        "severity": "HIGH",
        "latitude": 22.5726,
        "longitude": 88.3639,
    }
    response = client.post("/api/v1/reports", json=payload)
    assert response.status_code == 401


def test_invalid_coordinates_rejected_422(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    """Invalid latitude or longitude coordinates should be rejected with 422."""
    payload = {
        "emergency_type": "FIRE",
        "description": "Out-of-bounds coordinate report",
        "severity": "HIGH",
        "latitude": 105.0,  # Invalid latitude > 90
        "longitude": 88.3639,
    }
    response = client.post(
        "/api/v1/reports", json=payload, headers=auth_headers_user1
    )
    assert response.status_code == 422


def test_create_report_creates_new_incident_with_defaults(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    """New report without matching incidents creates a new Incident with UNVERIFIED status."""
    payload = {
        "emergency_type": "FIRE",
        "description": "Large market blaze",
        "severity": "HIGH",
        "latitude": 22.5726,
        "longitude": 88.3639,
    }
    response = client.post(
        "/api/v1/reports", json=payload, headers=auth_headers_user1
    )
    assert response.status_code == 201

    data = response.json()
    assert "report" in data
    assert "incident" in data

    report = data["report"]
    incident = data["incident"]

    assert report["emergency_type"] == "FIRE"
    assert report["severity"] == "HIGH"
    assert report["latitude"] == 22.5726
    assert report["longitude"] == 88.3639
    assert report["is_independent"] is True
    assert report["incident_id"] == incident["id"]

    assert incident["status"] == "UNVERIFIED"
    assert incident["confidence_score"] > 0.0
    assert incident["corroboration_count"] == 1


def test_nearby_report_attaches_to_existing_incident_and_increments_corroboration(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    auth_headers_user2: dict[str, str],
) -> None:
    """Second independent nearby report attaches to existing incident and increments corroboration."""
    payload1 = {
        "emergency_type": "FIRE",
        "description": "Flames near store entrance",
        "severity": "MEDIUM",
        "latitude": 22.5726,
        "longitude": 88.3639,
    }
    resp1 = client.post(
        "/api/v1/reports", json=payload1, headers=auth_headers_user1
    )
    assert resp1.status_code == 201
    incident1_id = resp1.json()["incident"]["id"]

    # User 2 reports ~200 meters away (0.002 deg latitude delta)
    payload2 = {
        "emergency_type": "FIRE",
        "description": "Thick black smoke visible from street",
        "severity": "HIGH",  # Higher severity escalates incident
        "latitude": 22.5746,
        "longitude": 88.3639,
    }
    resp2 = client.post(
        "/api/v1/reports", json=payload2, headers=auth_headers_user2
    )
    assert resp2.status_code == 201

    data2 = resp2.json()
    assert data2["report"]["incident_id"] == incident1_id
    assert data2["report"]["is_independent"] is True
    assert data2["incident"]["id"] == incident1_id
    assert data2["incident"]["corroboration_count"] == 2


def test_different_emergency_type_creates_distinct_incident(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    auth_headers_user2: dict[str, str],
) -> None:
    """Different emergency types at the same coordinates create distinct incidents."""
    resp1 = client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "FIRE",
            "description": "Building fire",
            "severity": "HIGH",
            "latitude": 22.5726,
            "longitude": 88.3639,
        },
        headers=auth_headers_user1,
    )
    resp2 = client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "ACCIDENT",
            "description": "Traffic collision nearby",
            "severity": "MEDIUM",
            "latitude": 22.5726,
            "longitude": 88.3639,
        },
        headers=auth_headers_user2,
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["incident"]["id"] != resp2.json()["incident"]["id"]


def test_distant_report_does_not_attach_to_incident(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    auth_headers_user2: dict[str, str],
) -> None:
    """Distant reports beyond the affected radius create a separate incident."""
    resp1 = client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "FIRE",
            "description": "South zone fire",
            "severity": "HIGH",
            "latitude": 22.5726,
            "longitude": 88.3639,
        },
        headers=auth_headers_user1,
    )
    # Coordinates in another district (several kilometers away)
    resp2 = client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "FIRE",
            "description": "North zone fire",
            "severity": "HIGH",
            "latitude": 22.6500,
            "longitude": 88.4000,
        },
        headers=auth_headers_user2,
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["incident"]["id"] != resp2.json()["incident"]["id"]


def test_repeated_report_from_same_user_is_not_independent(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    """Repeated report from the same user for an incident does not increment corroboration count."""
    payload = {
        "emergency_type": "FLOOD",
        "description": "Water rising rapidly",
        "severity": "HIGH",
        "latitude": 22.5726,
        "longitude": 88.3639,
    }
    resp1 = client.post(
        "/api/v1/reports", json=payload, headers=auth_headers_user1
    )
    assert resp1.status_code == 201
    assert resp1.json()["report"]["is_independent"] is True
    assert resp1.json()["incident"]["corroboration_count"] == 1

    # Same user submits another report for the same flood incident
    resp2 = client.post(
        "/api/v1/reports", json=payload, headers=auth_headers_user1
    )
    assert resp2.status_code == 201
    assert resp2.json()["report"]["is_independent"] is False
    assert resp2.json()["incident"]["corroboration_count"] == 1


def test_get_report_by_id(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    """Owner can retrieve their submitted report by ID."""
    create_resp = client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "MEDICAL",
            "description": "Individual needs immediate paramedic assistance",
            "severity": "CRITICAL",
            "latitude": 22.5726,
            "longitude": 88.3639,
        },
        headers=auth_headers_user1,
    )
    report_id = create_resp.json()["report"]["id"]

    get_resp = client.get(
        f"/api/v1/reports/{report_id}", headers=auth_headers_user1
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == report_id
    assert get_resp.json()["emergency_type"] == "MEDICAL"


def test_get_nonexistent_report_returns_404(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    """Requesting a nonexistent report returns 404."""
    response = client.get(
        "/api/v1/reports/nonexistent-uuid-1234", headers=auth_headers_user1
    )
    assert response.status_code == 404


def test_active_incidents_listing_and_filtering(
    client: TestClient,
    test_session: Session,
    auth_headers_user1: dict[str, str],
) -> None:
    """Listing active incidents excludes resolved and respects radius filtering."""
    # Create active incident via report
    client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "FIRE",
            "description": "Active downtown fire",
            "severity": "HIGH",
            "latitude": 22.5726,
            "longitude": 88.3639,
        },
        headers=auth_headers_user1,
    )

    # Manually create a resolved incident directly in db
    resolved_inc = Incident(
        emergency_type=EmergencyType.FIRE,
        title="Resolved Fire",
        severity=SeverityLevel.LOW,
        status=IncidentStatus.RESOLVED,
        latitude=22.5726,
        longitude=88.3639,
    )
    test_session.add(resolved_inc)
    test_session.commit()

    # Query active incidents
    resp = client.get("/api/v1/incidents")
    assert resp.status_code == 200
    incidents = resp.json()
    assert len(incidents) == 1
    assert incidents[0]["status"] != "RESOLVED"

    # Query with radius filter that includes the active incident
    resp_near = client.get(
        "/api/v1/incidents",
        params={"latitude": 22.5726, "longitude": 88.3639, "radius_meters": 1000},
    )
    assert resp_near.status_code == 200
    assert len(resp_near.json()) == 1

    # Query with radius filter from distant coordinates that excludes the incident
    resp_far = client.get(
        "/api/v1/incidents",
        params={"latitude": 28.6139, "longitude": 77.2090, "radius_meters": 5000},
    )
    assert resp_far.status_code == 200
    assert len(resp_far.json()) == 0
