"""Tests for authentication endpoints, token issuance, and current user retrieval."""

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
from app.models.user import User
from app.services.auth import get_user_by_email


@pytest.fixture
def test_session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory SQLite database session for auth tests."""
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


def test_registration_success(client: TestClient, test_session: Session) -> None:
    """Test user registration returns 201 and persists hashed password."""
    payload = {
        "email": "test.user@example.com",
        "password": "securepassword123",
        "full_name": "Test User",
        "phone_number": "+1234567890",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "test.user@example.com"
    assert data["full_name"] == "Test User"
    assert data["is_active"] is True
    assert "password" not in data
    assert "hashed_password" not in data

    # Verify database persistence
    db_user = get_user_by_email(test_session, "test.user@example.com")
    assert db_user is not None
    assert db_user.hashed_password != "securepassword123"
    assert db_user.hashed_password.startswith("$2b$")


def test_registration_duplicate_email(client: TestClient) -> None:
    """Test registering an existing email returns 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "mypassword123",
    }
    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


def test_login_success(client: TestClient) -> None:
    """Test logging in with valid credentials returns an access token."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "login.test@example.com", "password": "correctpassword"},
    )

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "login.test@example.com", "password": "correctpassword"},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert len(token_data["access_token"]) > 20


def test_login_invalid_password(client: TestClient) -> None:
    """Test login with wrong password returns 401 Unauthorized."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "password": "correctpassword"},
    )

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "incorrectpassword"},
    )
    assert login_resp.status_code == 401
    assert "incorrect email or password" in login_resp.json()["detail"].lower()


def test_login_unknown_email(client: TestClient) -> None:
    """Test login with non-existent email returns 401 Unauthorized."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "anyPassword123"},
    )
    assert login_resp.status_code == 401
    assert "incorrect email or password" in login_resp.json()["detail"].lower()


def test_get_current_user_me(client: TestClient) -> None:
    """Test GET /api/v1/auth/me with valid Bearer token."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "me.profile@example.com",
            "password": "profilepassword123",
            "full_name": "Profile Owner",
        },
    )

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "me.profile@example.com", "password": "profilepassword123"},
    )
    token = login_resp.json()["access_token"]

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "me.profile@example.com"
    assert me_data["full_name"] == "Profile Owner"
    assert "password" not in me_data
    assert "hashed_password" not in me_data


def test_get_current_user_missing_token(client: TestClient) -> None:
    """Test GET /api/v1/auth/me rejects requests without token with 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token(client: TestClient) -> None:
    """Test GET /api/v1/auth/me rejects invalid token with 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.malformed.jwt.token"},
    )
    assert response.status_code == 401


def test_inactive_user_cannot_authenticate(
    client: TestClient, test_session: Session
) -> None:
    """Test inactive users are rejected during login and token validation."""
    inactive_user = User(
        email="inactive@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=False,
    )
    test_session.add(inactive_user)
    test_session.commit()
    test_session.refresh(inactive_user)

    # Attempt login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 401
    assert "inactive" in login_resp.json()["detail"].lower()

    # Attempt using token created for inactive user
    token = create_access_token(subject=inactive_user.id)
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 401
    assert "inactive" in me_resp.json()["detail"].lower()


def test_email_normalization(client: TestClient) -> None:
    """Test email casing normalization on registration and login."""
    # Register with mixed casing
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "Citizen.User@Example.COM", "password": "normpassword123"},
    )
    assert reg_resp.status_code == 201
    assert reg_resp.json()["email"] == "citizen.user@example.com"

    # Login with all lowercase
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "citizen.user@example.com", "password": "normpassword123"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # Login with all uppercase
    login_resp2 = client.post(
        "/api/v1/auth/login",
        json={"email": "CITIZEN.USER@EXAMPLE.COM", "password": "normpassword123"},
    )
    assert login_resp2.status_code == 200

    # Attempt duplicate registration with different casing
    dup_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "CITIZEN.USER@EXAMPLE.COM", "password": "anotherpassword"},
    )
    assert dup_resp.status_code == 409
