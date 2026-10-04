"""Tests for emergency reporting photo attachment, validation, and storage."""

from collections.abc import Generator
import io
import os
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
from app.models.user import User


@pytest.fixture
def test_session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory SQLite database session."""
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
    """Create test reporter user and return Authorization headers."""
    user = User(
        email="photoreporter@example.com",
        hashed_password="hashed_pwd",
        full_name="Photo Reporter",
    )
    test_session.add(user)
    test_session.commit()
    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def responder_headers(test_session: Session) -> dict[str, str]:
    """Create test responder and return Authorization headers."""
    user = User(
        email="photoresponder@example.com",
        hashed_password="hashed_pwd",
        full_name="Photo Responder",
        is_responder=True,
    )
    test_session.add(user)
    test_session.commit()
    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


def test_report_without_photo_json_still_works(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Standard JSON report submission without photo remains fully functional."""
    payload = {
        "emergency_type": "FIRE",
        "description": "Visible flames from rooftop without photo",
        "severity": "HIGH",
        "latitude": 22.5726,
        "longitude": 88.3639,
    }
    response = client.post("/api/v1/reports", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["report"]["photo_url"] is None
    assert data["report"]["emergency_type"] == "FIRE"


def test_report_without_photo_multipart_works(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Multipart form data report submission without photo works gracefully."""
    form_data = {
        "emergency_type": "ACCIDENT",
        "description": "Multi-car collision on freeway ramp",
        "severity": "MEDIUM",
        "latitude": "22.5730",
        "longitude": "88.3640",
    }
    response = client.post("/api/v1/reports", data=form_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["report"]["photo_url"] is None
    assert data["report"]["emergency_type"] == "ACCIDENT"


def test_valid_jpeg_upload_works(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Uploading a valid JPEG image saves file with safe UUID and returns photo_url."""
    fake_jpeg_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"A" * 500
    files = {
        "photo": ("test_smoke.jpg", io.BytesIO(fake_jpeg_content), "image/jpeg")
    }
    data = {
        "emergency_type": "FIRE",
        "description": "Heavy black smoke captured from safe distance",
        "severity": "CRITICAL",
        "latitude": "22.5740",
        "longitude": "88.3650",
    }
    response = client.post(
        "/api/v1/reports", data=data, files=files, headers=auth_headers
    )
    assert response.status_code == 201
    res_json = response.json()
    photo_url = res_json["report"]["photo_url"]
    assert photo_url is not None
    assert photo_url.startswith("/uploads/report_photos/")
    assert photo_url.endswith(".jpg")
    # Verify safe UUID filename (32 hex chars + .jpg = 36 chars)
    filename = photo_url.split("/")[-1]
    assert len(filename) == 32 + 4  # hex + .jpg


def test_valid_png_upload_works(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Uploading a valid PNG image saves file and returns proper photo_url."""
    fake_png_content = b"\x89PNG\r\n\x1a\n" + b"P" * 300
    files = {
        "photo": ("evidence.png", io.BytesIO(fake_png_content), "image/png")
    }
    data = {
        "emergency_type": "FLOOD",
        "description": "Water level reaching building stairs",
        "severity": "HIGH",
        "latitude": "22.5710",
        "longitude": "88.3620",
    }
    response = client.post(
        "/api/v1/reports", data=data, files=files, headers=auth_headers
    )
    assert response.status_code == 201
    photo_url = response.json()["report"]["photo_url"]
    assert photo_url is not None
    assert photo_url.endswith(".png")


def test_valid_webp_upload_works(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Uploading a valid WebP image saves file and returns proper photo_url."""
    fake_webp_content = b"RIFF....WEBPVP8 " + b"W" * 200
    files = {
        "photo": ("snapshot.webp", io.BytesIO(fake_webp_content), "image/webp")
    }
    data = {
        "emergency_type": "UNSAFE_SITUATION",
        "description": "Downed electrical wire sparking in alleyway",
        "severity": "HIGH",
        "latitude": "22.5750",
        "longitude": "88.3660",
    }
    response = client.post(
        "/api/v1/reports", data=data, files=files, headers=auth_headers
    )
    assert response.status_code == 201
    photo_url = response.json()["report"]["photo_url"]
    assert photo_url is not None
    assert photo_url.endswith(".webp")


def test_invalid_mime_type_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Uploading non-image files (e.g. PDF or executable) is rejected with 400."""
    fake_pdf = b"%PDF-1.4 " + b"X" * 100
    files = {
        "photo": ("document.pdf", io.BytesIO(fake_pdf), "application/pdf")
    }
    data = {
        "emergency_type": "FIRE",
        "description": "Attempting invalid attachment format",
        "severity": "LOW",
        "latitude": "22.5726",
        "longitude": "88.3639",
    }
    response = client.post(
        "/api/v1/reports", data=data, files=files, headers=auth_headers
    )
    assert response.status_code == 400
    assert "Invalid image type" in response.json()["detail"]


def test_oversized_image_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Uploading files larger than 5MB is rejected with 413."""
    # 5MB + 1024 bytes
    oversized_content = b"\xFF\xD8\xFF\xE0" + b"0" * (5 * 1024 * 1024 + 1024)
    files = {
        "photo": ("huge_photo.jpg", io.BytesIO(oversized_content), "image/jpeg")
    }
    data = {
        "emergency_type": "FIRE",
        "description": "Attempting oversized image submission",
        "severity": "HIGH",
        "latitude": "22.5726",
        "longitude": "88.3639",
    }
    response = client.post(
        "/api/v1/reports", data=data, files=files, headers=auth_headers
    )
    assert response.status_code == 413
    assert "5MB" in response.json()["detail"]


def test_evidence_photos_exposed_in_incident_details(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Incident details expose evidence_photos list containing uploaded photo URLs."""
    fake_jpeg = b"\xFF\xD8\xFF\xE0" + b"J" * 200
    files = {
        "photo": ("fire_evidence.jpg", io.BytesIO(fake_jpeg), "image/jpeg")
    }
    data = {
        "emergency_type": "FIRE",
        "description": "Industrial smoke stack fire with photo evidence",
        "severity": "CRITICAL",
        "latitude": "22.6000",
        "longitude": "88.4000",
    }
    rep_res = client.post(
        "/api/v1/reports", data=data, files=files, headers=auth_headers
    )
    assert rep_res.status_code == 201
    inc_id = rep_res.json()["incident"]["id"]
    photo_url = rep_res.json()["report"]["photo_url"]

    # Read incident detail
    inc_res = client.get(f"/api/v1/incidents/{inc_id}")
    assert inc_res.status_code == 200
    detail = inc_res.json()
    assert "evidence_photos" in detail
    assert photo_url in detail["evidence_photos"]


def test_unauthorized_user_cannot_access_private_report(
    client: TestClient,
    test_session: Session,
    auth_headers: dict[str, str],
) -> None:
    """Regular user cannot access another user's single report via GET /reports/{id}."""
    # Create report by user 1
    data = {
        "emergency_type": "FIRE",
        "description": "Confidential observation with photo",
        "severity": "MEDIUM",
        "latitude": 22.5726,
        "longitude": 88.3639,
    }
    res = client.post("/api/v1/reports", json=data, headers=auth_headers)
    assert res.status_code == 201
    report_id = res.json()["report"]["id"]

    # Create user 2
    user2 = User(
        email="stranger@example.com",
        hashed_password="pw",
        full_name="Stranger User",
    )
    test_session.add(user2)
    test_session.commit()
    token2 = create_access_token(subject=user2.id)
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 2 tries to read user 1's report directly
    get_res = client.get(f"/api/v1/reports/{report_id}", headers=headers2)
    assert get_res.status_code == 403
    assert "Not authorized" in get_res.json()["detail"]
