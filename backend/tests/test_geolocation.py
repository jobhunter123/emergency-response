"""Unit tests for Haversine distance calculations and radius checks."""

import pytest

from app.services.geolocation import (
    calculate_distance_meters,
    is_within_radius,
)


def test_distance_same_coordinates() -> None:
    """Distance between identical coordinates should be approximately 0 meters."""
    lat = 22.5726
    lon = 88.3639
    distance = calculate_distance_meters(lat, lon, lat, lon)
    assert distance == pytest.approx(0.0, abs=1e-3)


def test_distance_known_nearby_coordinates() -> None:
    """Check distance between two points approximately 500m apart in Kolkata."""
    # Point 1: 22.5726, 88.3639
    # Point 2: ~440-500 meters away (0.004 degrees north is ~444 meters)
    lat1, lon1 = 22.5726, 88.3639
    lat2, lon2 = 22.5766, 88.3639
    distance = calculate_distance_meters(lat1, lon1, lat2, lon2)
    assert 400.0 < distance < 500.0


def test_is_within_radius_true() -> None:
    """Points within the specified radius threshold should return True."""
    lat1, lon1 = 22.5726, 88.3639
    lat2, lon2 = 22.5746, 88.3639  # ~222 meters apart
    assert is_within_radius(lat1, lon1, lat2, lon2, radius_meters=300.0) is True


def test_is_within_radius_false() -> None:
    """Points exceeding the specified radius threshold should return False."""
    lat1, lon1 = 22.5726, 88.3639
    lat2, lon2 = 22.5826, 88.3639  # ~1110 meters apart
    assert is_within_radius(lat1, lon1, lat2, lon2, radius_meters=500.0) is False
