"""Affected area spatial calculations and affected user discovery services."""

import math
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.user import User
from app.services.geolocation import is_within_radius

METERS_PER_DEGREE_LAT: float = 111320.0


def calculate_bounding_box(
    latitude: float, longitude: float, radius_meters: float
) -> dict[str, float]:
    """Calculate approximate north, south, east, and west bounding coordinates for a radius in meters.

    Args:
        latitude: Center latitude in degrees.
        longitude: Center longitude in degrees.
        radius_meters: Radius in meters.

    Returns:
        Dictionary containing north, south, east, and west bounds in degrees.
    """
    delta_lat = radius_meters / METERS_PER_DEGREE_LAT
    lat_rad = math.radians(latitude)
    cos_lat = math.cos(lat_rad)
    delta_lon = (
        radius_meters / (METERS_PER_DEGREE_LAT * cos_lat)
        if abs(cos_lat) > 1e-6
        else 180.0
    )

    return {
        "north": min(90.0, latitude + delta_lat),
        "south": max(-90.0, latitude - delta_lat),
        "east": min(180.0, longitude + delta_lon),
        "west": max(-180.0, longitude - delta_lon),
    }


def calculate_affected_area(incident: Incident) -> dict[str, Any]:
    """Calculate the geographic affected area representation for an incident.

    Args:
        incident: Target Incident entity with latitude, longitude, and affected_radius_meters.

    Returns:
        Structured dictionary with center coordinates, radius in meters, and bounding coordinates.
    """
    return {
        "center": {
            "latitude": incident.latitude,
            "longitude": incident.longitude,
        },
        "radius_meters": incident.affected_radius_meters,
        "bounds": calculate_bounding_box(
            latitude=incident.latitude,
            longitude=incident.longitude,
            radius_meters=incident.affected_radius_meters,
        ),
    }


def is_location_affected(
    latitude: float,
    longitude: float,
    incident: Incident,
) -> bool:
    """Determine whether a given coordinate point falls within the incident's affected radius.

    Delegates to the existing Haversine implementation in app.services.geolocation.

    Args:
        latitude: Target latitude in degrees.
        longitude: Target longitude in degrees.
        incident: Target Incident entity.

    Returns:
        True if the location is within the incident's affected radius, False otherwise.
    """
    return is_within_radius(
        lat1=latitude,
        lon1=longitude,
        lat2=incident.latitude,
        lon2=incident.longitude,
        radius_meters=incident.affected_radius_meters,
    )


def find_affected_users(db: Session, incident: Incident) -> list[User]:
    """Find all active users currently located within the incident's affected geographic radius.

    Args:
        db: SQLAlchemy database session.
        incident: Target Incident entity.

    Returns:
        List of active User entities within the incident's affected radius.
    """
    stmt = select(User).where(
        User.is_active.is_(True),
        User.latitude.is_not(None),
        User.longitude.is_not(None),
    )
    active_users_with_location = db.execute(stmt).scalars().all()

    affected_users: list[User] = []
    for user in active_users_with_location:
        if user.latitude is not None and user.longitude is not None:
            if is_location_affected(user.latitude, user.longitude, incident):
                affected_users.append(user)

    return affected_users


def count_affected_users(db: Session, incident: Incident) -> int:
    """Return the total count of active users currently within the incident's affected radius.

    Args:
        db: SQLAlchemy database session.
        incident: Target Incident entity.

    Returns:
        Non-negative integer representing the aggregate affected user count.
    """
    return len(find_affected_users(db=db, incident=incident))
