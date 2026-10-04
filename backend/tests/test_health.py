"""Tests for service health and root endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    """Test that the health check endpoint returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint() -> None:
    """Test that the root endpoint returns 200 and basic API identification."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "docs_url" in data
