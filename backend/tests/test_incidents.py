"""Tests for incidents API endpoints."""

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
from app.models.enums import EmergencyType, SeverityLevel
from app.models.incident import Incident
from app.models.user import User


@pytest.fixture
def test_session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory SQLite database session for incident tests."""
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
def auth_headers(test_session: Session) -> dict[str, str]:
    """Create a user and return authorization bearer headers."""
    user = User(
        email="incident_tester@example.com",
        hashed_password="pw",
    )
    test_session.add(user)
    test_session.commit()
    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


def test_get_incident_detail_with_report_count(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """GET /api/v1/incidents/{incident_id} returns incident details and report count."""
    # Create two reports that cluster into the same incident
    client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "ACCIDENT",
            "description": "Multi-car collision on flyover",
            "severity": "HIGH",
            "latitude": 22.5726,
            "longitude": 88.3639,
        },
        headers=auth_headers,
    )
    rep2 = client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "ACCIDENT",
            "description": "Ambulance en route to flyover",
            "severity": "CRITICAL",
            "latitude": 22.5728,
            "longitude": 88.3640,
        },
        headers=auth_headers,
    )
    incident_id = rep2.json()["incident"]["id"]

    # Fetch incident detail
    resp = client.get(f"/api/v1/incidents/{incident_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == incident_id
    assert data["emergency_type"] == "ACCIDENT"
    assert data["severity"] == "CRITICAL"
    assert data["report_count"] == 2


def test_get_unknown_incident_returns_404(client: TestClient) -> None:
    """GET /api/v1/incidents/{incident_id} with unknown ID returns 404."""
    response = client.get("/api/v1/incidents/unknown-uuid-999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_active_incident_listing(client: TestClient, test_session: Session) -> None:
    """GET /api/v1/incidents lists all active incidents."""
    inc1 = Incident(
        emergency_type=EmergencyType.STORM,
        title="Cyclone Warning",
        severity=SeverityLevel.HIGH,
        latitude=22.5,
        longitude=88.3,
    )
    inc2 = Incident(
        emergency_type=EmergencyType.EARTHQUAKE,
        title="Tremor Observed",
        severity=SeverityLevel.MEDIUM,
        latitude=22.6,
        longitude=88.4,
    )
    test_session.add_all([inc1, inc2])
    test_session.commit()

    response = client.get("/api/v1/incidents")
    assert response.status_code == 200
    ids = {i["id"] for i in response.json()}
    assert inc1.id in ids
    assert inc2.id in ids
