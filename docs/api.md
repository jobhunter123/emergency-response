# API Specification — Signal Emergency Response Platform

This document details the REST API endpoints, schemas, authentication requirements, operational state transitions, and confidence scoring rules implemented in the Signal Emergency Response Platform backend.

---

## 1. Base URL & Interactive Documentation

- **Base URL**: `http://127.0.0.1:8000/api/v1`
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 2. Authentication & Authorization

All protected endpoints require a valid JWT Bearer token in the `Authorization` header:

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

- **Algorithm**: `HS256`
- **Subject (`sub`)**: User UUID string
- **Default Lifetime**: 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)

### 2.1 Register User
- **Endpoint**: `POST /api/v1/auth/register`
- **Auth Required**: No
- **Request Body** (`application/json`):
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "Jane Citizen",
    "phone_number": "+1555123456"
  }
  ```
- **Responses**:
  - `201 Created`: Returns `UserResponse` (`id`, `email`, `full_name`, `is_active`, `is_responder`, etc.).
  - `409 Conflict`: If email is already registered.
  - `422 Unprocessable Entity`: Validation failure.

### 2.2 Login (OAuth2 Password Grant)
- **Endpoint**: `POST /api/v1/auth/login`
- **Auth Required**: No
- **Request Body** (`application/x-www-form-urlencoded` or `application/json`):
  ```text
  username=user@example.com&password=SecurePassword123!
  ```
- **Responses**:
  - `200 OK`:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    }
    ```
  - `401 Unauthorized`: Invalid email or password.

### 2.3 Get Current User Profile
- **Endpoint**: `GET /api/v1/auth/me`
- **Auth Required**: Yes (Bearer token)
- **Responses**:
  - `200 OK`: Returns current authenticated `UserResponse`.
  - `401 Unauthorized`: Missing or expired token.

---

## 3. User Location Snapshot

### 3.1 Update User Location Snapshot
- **Endpoint**: `PATCH /api/v1/users/me/location`
- **Auth Required**: Yes
- **Description**: Updates the user's point-in-time geographic coordinates. Does not retain historical tracks.
- **Request Body**:
  ```json
  {
    "latitude": 22.5726,
    "longitude": 88.3639
  }
  ```
- **Responses**:
  - `200 OK`: Returns updated `UserResponse` with `latitude`, `longitude`, and `location_updated_at`.

---

## 4. Emergency Reports & Spatial Clustering

### 4.1 Submit Emergency Report
- **Endpoint**: `POST /api/v1/reports`
- **Auth Required**: Yes
- **Description**: Submits an individual emergency observation. Automatically clusters with matching active incidents within 500m and 60 minutes, or initializes a new incident. Dynamically recalculates confidence score. Supports optional on-scene photo evidence.
- **Content Types**:
  - `application/json` (standard report without photo)
  - `multipart/form-data` (report with optional attached photo)
- **Form / JSON Fields**:
  - `emergency_type`: Enum (`FIRE`, `ACCIDENT`, `FLOOD`, `MEDICAL`, `EARTHQUAKE`, `STORM`, `LANDSLIDE`, `MISSING_PERSON`, `UNSAFE_SITUATION`, `OTHER`)
  - `description`: String (5–1000 characters)
  - `severity`: Enum (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - `latitude`: Float (-90.0 to 90.0)
  - `longitude`: Float (-180.0 to 180.0)
  - `photo`: File upload (optional, max 5 MB; allowed MIME types: `image/jpeg`, `image/png`, `image/webp`)
- **Validation & Storage**:
  - File size strictly capped at 5 MB (5,242,880 bytes); larger uploads return `413 Request Entity Too Large`.
  - MIME type verified against whitelist; non-image formats return `400 Bad Request`.
  - Safe UUID-based filename is generated (`<uuid>.<ext>`); original client filenames are never used directly on the filesystem.
  - Stored in `backend/uploads/report_photos/` and served via controlled static route `/uploads/report_photos/<filename>`.
- **Responses**:
  - `201 Created`:
    ```json
    {
      "report": {
        "id": "report-uuid",
        "user_id": "user-uuid",
        "incident_id": "incident-uuid",
        "emergency_type": "FIRE",
        "description": "Heavy smoke pouring from 3rd floor...",
        "severity": "CRITICAL",
        "latitude": 22.5726,
        "longitude": 88.3639,
        "photo_url": "/uploads/report_photos/e6faedef388d4df7bb0e1d8c7ae3c515.jpg",
        "reported_at": "2026-10-04T12:00:00Z",
        "confidence_contribution": 25.0,
        "is_independent": true
      },
      "incident": {
        "id": "incident-uuid",
        "status": "UNVERIFIED",
        "confidence_score": 55.0,
        "corroboration_count": 1,
        "confidence_level": "HIGH"
      }
    }
    ```
  - `400 Bad Request`: Invalid image format or corrupt upload.
  - `413 Request Entity Too Large`: Image exceeds 5 MB size limit.
  - `422 Unprocessable Entity`: Validation failure on coordinates or text fields.

### 4.2 Retrieve Report by ID
- **Endpoint**: `GET /api/v1/reports/{report_id}`
- **Auth Required**: Yes (Must be the report author or a verified responder)
- **Responses**:
  - `200 OK`: Returns `EmergencyReportResponse` including `photo_url`.
  - `403 Forbidden`: Unauthorized user.
  - `404 Not Found`: Report does not exist.

### 4.3 Static Photo Evidence Route
- **Endpoint**: `GET /uploads/report_photos/{filename}`
- **Auth Required**: No (Direct controlled static file serving)
- **Description**: Serves verified evidence photos uploaded by citizens. Filenames are non-enumerable UUIDs to prevent enumeration. Path traversal is strictly prevented.

---

## 5. Incidents & Affected Area

### 5.1 List Active Incidents
- **Endpoint**: `GET /api/v1/incidents`
- **Auth Required**: Optional
- **Query Parameters**:
  - `emergency_type` (optional): Filter by incident type.
  - `severity` (optional): Filter by severity level.
  - `latitude`, `longitude`, `radius_meters` (optional): Spatial bounding filter.
- **Responses**:
  - `200 OK`: Array of `IncidentListItem` objects (excludes `RESOLVED` and `FALSE_ALARM`).

### 5.2 Get Incident Details
- **Endpoint**: `GET /api/v1/incidents/{incident_id}`
- **Auth Required**: Optional
- **Responses**:
  - `200 OK`:
    ```json
    {
      "id": "incident-uuid",
      "title": "Fire Incident",
      "description": "Visible heavy smoke pouring from warehouse",
      "emergency_type": "FIRE",
      "severity": "CRITICAL",
      "status": "CONFIRMED",
      "latitude": 22.5726,
      "longitude": 88.3639,
      "affected_radius_meters": 500.0,
      "confidence_score": 75.0,
      "confidence_level": "VERY_HIGH",
      "corroboration_count": 2,
      "report_count": 2,
      "confirmed_at": "2026-10-04T12:05:00Z",
      "affected_area": {
        "center": {
          "latitude": 22.5726,
          "longitude": 88.3639
        },
        "radius_meters": 500.0,
        "bounds": {
          "north": 22.5771,
          "south": 22.5681,
          "east": 88.3688,
          "west": 88.3590
        }
      },
      "affected_user_count": 4,
      "created_at": "2026-10-04T12:00:00Z",
      "updated_at": "2026-10-04T12:05:00Z"
    }
    ```

---

## 6. Responder Operational Lifecycle

### 6.1 Update Incident Status
- **Endpoint**: `PATCH /api/v1/incidents/{incident_id}/status`
- **Auth Required**: Yes (Must have `is_responder: true`)
- **Request Body**:
  ```json
  {
    "status": "CONFIRMED"
  }
  ```
- **Allowed Operational Transitions**:
  - `UNVERIFIED` → `VERIFYING`, `FALSE_ALARM`
  - `VERIFYING` → `CONFIRMED`, `FALSE_ALARM`
  - `CONFIRMED` → `RESPONDING`, `FALSE_ALARM`
  - `RESPONDING` → `CONTAINED`, `FALSE_ALARM`
  - `CONTAINED` → `RESOLVED`
  - `RESOLVED` → *None (Terminal)*
  - `FALSE_ALARM` → *None (Terminal)*
- **Side Effects**:
  - `CONFIRMED`: Sets `confirmed_at` timestamp; triggers targeted alerts for users within affected radius.
  - `RESPONDING`: Triggers targeted alerts for newly affected users with deduplication.
- **Responses**:
  - `200 OK`: Returns updated `IncidentDetailResponse`.
  - `400 Bad Request`: Invalid transition (e.g. backward transition).
  - `403 Forbidden`: User is not a verified responder.

---

## 7. Targeted Alerts

### 7.1 List User Alerts
- **Endpoint**: `GET /api/v1/alerts`
- **Auth Required**: Yes
- **Query Parameters**:
  - `unread_only` (bool, default `false`): If `true`, returns only unread alerts.
- **Responses**:
  - `200 OK`: Array of `AlertResponse` objects addressed to the authenticated user.
    ```json
    [
      {
        "id": "alert-uuid",
        "incident_id": "incident-uuid",
        "user_id": "user-uuid",
        "title": "CRITICAL Alert: Fire",
        "message": "A critical fire emergency has been confirmed near your location...",
        "severity": "CRITICAL",
        "is_read": false,
        "read_at": null,
        "created_at": "2026-10-04T12:05:00Z"
      }
    ]
    ```

### 7.2 Mark Alert as Read
- **Endpoint**: `PATCH /api/v1/alerts/{alert_id}/read`
- **Auth Required**: Yes (Recipient only)
- **Responses**:
  - `200 OK`: Returns updated `AlertResponse` with `is_read = true` and `read_at = timestamp`.
  - `403 Forbidden`: If alert belongs to another user.
  - `404 Not Found`: Alert not found.

---

## 8. Confidence Scoring Formulation

$$\text{Score} = \text{Base Corroboration} (0-75) + \text{Geographic Bonus} (0-15) + \text{Temporal Bonus} (0-10) + \text{Severity Bonus} (0-5)$$

- **Independent Reports Base**:
  - 1 report: 25.0
  - 2 reports: 45.0
  - 3 reports: 60.0
  - 4 reports: 70.0
  - 5+ reports: 75.0
- **Tiers**:
  - `0.0 – 24.9`: `LOW`
  - `25.0 – 49.9`: `MODERATE` (Triggers `VERIFYING` if $\ge 2$ independent reports)
  - `50.0 – 74.9`: `HIGH`
  - `75.0 – 100.0`: `VERY_HIGH`
