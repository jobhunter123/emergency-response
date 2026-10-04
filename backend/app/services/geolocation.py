"""Geolocation calculations and spatial distance helper utilities."""

import math

EARTH_RADIUS_METERS: float = 6371000.0


def calculate_distance_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate the great-circle distance between two geographic coordinates in meters.

    Uses the standard Haversine formula:
    a = sin²(Δφ/2) + cos(φ1) * cos(φ2) * sin²(Δλ/2)
    c = 2 * atan2(√a, √(1−a))
    d = R * c

    Args:
        lat1: Latitude of point 1 in degrees.
        lon1: Longitude of point 1 in degrees.
        lat2: Latitude of point 2 in degrees.
        lon2: Longitude of point 2 in degrees.

    Returns:
        Approximate distance in meters.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_METERS * c


def is_within_radius(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    radius_meters: float,
) -> bool:
    """Determine whether two coordinates are within a specified distance in meters.

    Args:
        lat1: Latitude of point 1 in degrees.
        lon1: Longitude of point 1 in degrees.
        lat2: Latitude of point 2 in degrees.
        lon2: Longitude of point 2 in degrees.
        radius_meters: Maximum distance threshold in meters.

    Returns:
        True if the distance between points <= radius_meters, False otherwise.
    """
    return calculate_distance_meters(lat1, lon1, lat2, lon2) <= radius_meters
