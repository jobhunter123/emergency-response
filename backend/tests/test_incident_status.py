"""Tests for responder operational lifecycle and incident status transitions."""

from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import EmergencyType, IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.user import User


@pytest.fixture
def test_session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory SQLite session for status transition tests."""
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
def normal_user_headers(test_session: Session) -> dict[str, str]:
    """Create a regular citizen user (is_responder=False)."""
    user = User(
        email="citizen@example.com",
        hashed_password=get_password_hash("pw"),
        is_responder=False,
    )
    test_session.add(user)
    test_session.commit()
    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def responder_headers(test_session: Session) -> dict[str, str]:
    """Create an authorized emergency responder (is_responder=True)."""
    user = User(
        email="responder@example.com",
        hashed_password=get_password_hash("pw"),
        is_responder=True,
    )
    test_session.add(user)
    test_session.commit()
    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_incident(test_session: Session) -> Incident:
    """Create a sample unverified incident."""
    incident = Incident(
        emergency_type=EmergencyType.FIRE,
        title="Sample Fire",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.UNVERIFIED,
        latitude=22.5726,
        longitude=88.3639,
    )
    test_session.add(incident)
    test_session.commit()
    test_session.refresh(incident)
    return incident


def test_non_responder_cannot_change_status(
    client: TestClient, sample_incident: Incident, normal_user_headers: dict[str, str]
) -> None:
    """1. Non-responder cannot change status (403 Forbidden)."""
    response = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "VERIFYING"},
        headers=normal_user_headers,
    )
    assert response.status_code == 403
    assert "responder" in response.json()["detail"].lower()


def test_unauthenticated_cannot_change_status(
    client: TestClient, sample_incident: Incident
) -> None:
    """2. Unauthenticated user cannot change status (401 Unauthorized)."""
    response = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "VERIFYING"},
    )
    assert response.status_code == 401


def test_responder_unverified_to_verifying(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """3. Responder can change UNVERIFIED -> VERIFYING."""
    response = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "VERIFYING"},
        headers=responder_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "VERIFYING"


def test_responder_verifying_to_confirmed_and_timestamp(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """4 & 5. Responder can change VERIFYING -> CONFIRMED and confirmed_at is populated."""
    # First move to VERIFYING
    client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "VERIFYING"},
        headers=responder_headers,
    )

    # Now transition to CONFIRMED
    resp = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "CONFIRMED"},
        headers=responder_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CONFIRMED"
    assert data["confirmed_at"] is not None


def test_responder_confirmed_to_responding(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """6. Responder can change CONFIRMED -> RESPONDING."""
    for st in ["VERIFYING", "CONFIRMED", "RESPONDING"]:
        resp = client.patch(
            f"/api/v1/incidents/{sample_incident.id}/status",
            json={"status": st},
            headers=responder_headers,
        )
        assert resp.status_code == 200
    assert resp.json()["status"] == "RESPONDING"


def test_responder_responding_to_contained(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """7. Responder can change RESPONDING -> CONTAINED."""
    for st in ["VERIFYING", "CONFIRMED", "RESPONDING", "CONTAINED"]:
        resp = client.patch(
            f"/api/v1/incidents/{sample_incident.id}/status",
            json={"status": st},
            headers=responder_headers,
        )
        assert resp.status_code == 200
    assert resp.json()["status"] == "CONTAINED"


def test_responder_contained_to_resolved(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """8. Responder can change CONTAINED -> RESOLVED."""
    for st in ["VERIFYING", "CONFIRMED", "RESPONDING", "CONTAINED", "RESOLVED"]:
        resp = client.patch(
            f"/api/v1/incidents/{sample_incident.id}/status",
            json={"status": st},
            headers=responder_headers,
        )
        assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVED"


def test_verifying_to_false_alarm(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """9. Responder can change VERIFYING -> FALSE_ALARM."""
    client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "VERIFYING"},
        headers=responder_headers,
    )
    resp = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "FALSE_ALARM"},
        headers=responder_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "FALSE_ALARM"


def test_confirmed_to_false_alarm(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """10. Responder can change CONFIRMED -> FALSE_ALARM."""
    client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "VERIFYING"},
        headers=responder_headers,
    )
    client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "CONFIRMED"},
        headers=responder_headers,
    )
    resp = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "FALSE_ALARM"},
        headers=responder_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "FALSE_ALARM"


def test_invalid_backward_transitions_return_400(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """11. Invalid backward transitions return 400 Bad Request."""
    # Move to CONTAINED
    for st in ["VERIFYING", "CONFIRMED", "RESPONDING", "CONTAINED"]:
        client.patch(
            f"/api/v1/incidents/{sample_incident.id}/status",
            json={"status": st},
            headers=responder_headers,
        )

    # Attempt CONTAINED -> VERIFYING (Invalid backward step)
    resp_backward = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "VERIFYING"},
        headers=responder_headers,
    )
    assert resp_backward.status_code == 400
    assert "invalid" in resp_backward.json()["detail"].lower()

    # Move to RESOLVED
    client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "RESOLVED"},
        headers=responder_headers,
    )

    # Attempt RESOLVED -> CONFIRMED
    resp_resolved_confirmed = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "CONFIRMED"},
        headers=responder_headers,
    )
    assert resp_resolved_confirmed.status_code == 400

    # Attempt RESOLVED -> RESPONDING
    resp_resolved_resp = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "RESPONDING"},
        headers=responder_headers,
    )
    assert resp_resolved_resp.status_code == 400


def test_false_alarm_cannot_transition(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """12. FALSE_ALARM cannot transition to CONFIRMED or other states."""
    client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "FALSE_ALARM"},
        headers=responder_headers,
    )
    resp = client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "CONFIRMED"},
        headers=responder_headers,
    )
    assert resp.status_code == 400


def test_resolved_cannot_transition(
    client: TestClient, sample_incident: Incident, responder_headers: dict[str, str]
) -> None:
    """13. RESOLVED cannot transition to another operational state."""
    for st in ["VERIFYING", "CONFIRMED", "RESPONDING", "CONTAINED", "RESOLVED"]:
        client.patch(
            f"/api/v1/incidents/{sample_incident.id}/status",
            json={"status": st},
            headers=responder_headers,
        )

    for target in ["UNVERIFIED", "VERIFYING", "RESPONDING", "CONTAINED", "FALSE_ALARM"]:
        resp = client.patch(
            f"/api/v1/incidents/{sample_incident.id}/status",
            json={"status": target},
            headers=responder_headers,
        )
        assert resp.status_code == 400


def test_high_confidence_never_automatically_confirms(
    client: TestClient, normal_user_headers: dict[str, str]
) -> None:
    """14. A high confidence score does not automatically change an incident to CONFIRMED."""
    # Submit first report
    r1 = client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "FIRE",
            "description": "Blaze",
            "severity": "CRITICAL",
            "latitude": 22.5726,
            "longitude": 88.3639,
        },
        headers=normal_user_headers,
    ).json()
    inc_id = r1["incident"]["id"]
    assert r1["incident"]["status"] == "UNVERIFIED"

    # Create 3 more users and submit nearby reports
    for i in range(3):
        client.post(
            "/api/v1/auth/register",
            json={"email": f"extra_user_{i}@example.com", "password": "Password123!"},
        )
        token = client.post(
            "/api/v1/auth/login",
            json={"email": f"extra_user_{i}@example.com", "password": "Password123!"},
        ).json()["access_token"]
        rep = client.post(
            "/api/v1/reports",
            json={
                "emergency_type": "FIRE",
                "description": f"Observation {i}",
                "severity": "CRITICAL",
                "latitude": 22.5727,
                "longitude": 88.3640,
            },
            headers={"Authorization": f"Bearer {token}"},
        ).json()

    # Fetch incident detail: status should be VERIFYING, NOT CONFIRMED
    detail = client.get(f"/api/v1/incidents/{inc_id}").json()
    assert detail["confidence_score"] >= 75.0
    assert detail["status"] == "VERIFYING"
    assert detail["status"] != "CONFIRMED"


def test_new_report_does_not_downgrade_confirmed_status(
    client: TestClient,
    sample_incident: Incident,
    responder_headers: dict[str, str],
    normal_user_headers: dict[str, str],
) -> None:
    """15. Submitting another report does not downgrade manually CONFIRMED status to VERIFYING."""
    # Responder confirms the incident
    client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "VERIFYING"},
        headers=responder_headers,
    )
    client.patch(
        f"/api/v1/incidents/{sample_incident.id}/status",
        json={"status": "CONFIRMED"},
        headers=responder_headers,
    )

    # Citizen submits a new nearby corroborating report
    client.post(
        "/api/v1/reports",
        json={
            "emergency_type": "FIRE",
            "description": "Fire truck arrives",
            "severity": "HIGH",
            "latitude": 22.5728,
            "longitude": 88.3639,
        },
        headers=normal_user_headers,
    )

    # Verify status is still CONFIRMED
    detail = client.get(f"/api/v1/incidents/{sample_incident.id}").json()
    assert detail["status"] == "CONFIRMED"
