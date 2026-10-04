"""Enums defining incident types, severity levels, and lifecycle statuses."""

import enum


class EmergencyType(str, enum.Enum):
    """Supported emergency report and incident categories."""

    FIRE = "FIRE"
    FLOOD = "FLOOD"
    ACCIDENT = "ACCIDENT"
    MEDICAL = "MEDICAL"
    EARTHQUAKE = "EARTHQUAKE"
    STORM = "STORM"
    LANDSLIDE = "LANDSLIDE"
    MISSING_PERSON = "MISSING_PERSON"
    UNSAFE_SITUATION = "UNSAFE_SITUATION"
    OTHER = "OTHER"


class SeverityLevel(str, enum.Enum):
    """Severity ratings for incidents and user reports."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, enum.Enum):
    """Lifecycle verification and response status of an incident."""

    UNVERIFIED = "UNVERIFIED"
    VERIFYING = "VERIFYING"
    CONFIRMED = "CONFIRMED"
    RESPONDING = "RESPONDING"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"
    FALSE_ALARM = "FALSE_ALARM"
