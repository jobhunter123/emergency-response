# System Architecture — Signal Emergency Response Platform

This document provides a comprehensive technical overview of the architecture, design principles, algorithms, and data flows implemented in the Signal Emergency Response Platform.

---

## 1. Architectural Philosophy

Signal is designed as a modular, lightweight, high-performance emergency coordination platform following these foundational principles:

1. **Deterministic Over Heuristic**: Critical emergency scoring must be mathematically deterministic and predictable, not reliant on opaque machine learning models or non-deterministic heuristics.
2. **Corroboration Before Action**: Citizen observations represent vital community signals, but no single report is treated as absolute truth.
3. **Strict Separation of Concerns**:
   - Citizens provide observations (`EmergencyReport`).
   - The platform calculates spatial clustering and corroboration strength (`confidence_score`).
   - Authorized first responders retain sovereign authority over official operational status (`IncidentStatus`).
4. **Zero Continuous Tracking**: To respect citizen privacy, the platform only retains a point-in-time snapshot of the user's location upon explicit user action. Historical location trails are never recorded.

---

## 2. High-Level Architecture Diagram

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (FRONTEND)                         │
│   React 19 • TypeScript • Vite 8 • CSS Tokens & Tailwind CSS v4        │
│   ├── Citizen View: Interactive Map, Emergency Form, Alerts Panel      │
│   └── Responder View: Incident Management, Lifecycle Actions           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST (JWT Bearer Auth)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        API LAYER (FASTAPI)                             │
│   ├── Authentication Router   (/api/v1/auth)                           │
│   ├── Emergency Reports Router (/api/v1/reports)                       │
│   ├── Incidents Router        (/api/v1/incidents)                     │
│   ├── Alerts Router           (/api/v1/alerts)                         │
│   └── Users Router            (/api/v1/users)                          │
├────────────────────────────────────────────────────────────────────────┤
│                      SERVICE & DOMAIN LOGIC LAYER                      │
│   ├── Geolocation Service: Haversine spherical distance calculations   │
│   ├── Clustering Engine: Proximity (500m) & temporal (60m) correlation │
│   ├── Confidence Engine: Deterministic bounded 0–100 scoring           │
│   ├── Incident State Machine: Responder lifecycle enforcement          │
│   ├── Affected Area Service: Impact radius & recipient discovery       │
│   └── Alert Generation Service: Targeted dispatch & deduplication      │
├────────────────────────────────────────────────────────────────────────┤
│                        DATA PERSISTENCE LAYER                          │
│   SQLAlchemy 2.x ORM • SQLite Embedded Database                        │
│   ├── Users Table (credentials, responder status, location snapshot)   │
│   ├── Incidents Table (cluster center, status, confidence score)       │
│   ├── Emergency Reports Table (type, location, severity, independence) │
│   └── Alerts Table (incident reference, user recipient, read state)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Domain Entities & Database Schema

```text
┌──────────────────────────────┐          ┌──────────────────────────────┐
│            User              │          │           Incident           │
├──────────────────────────────┤          ├──────────────────────────────┤
│ id (UUID, PK)                │          │ id (UUID, PK)                │
│ email (Unique, Indexed)      │          │ title (String)               │
│ hashed_password (String)     │          │ description (Text)           │
│ full_name (String)           │          │ emergency_type (Enum)        │
│ phone_number (String, Null)  │          │ severity (Enum)              │
│ is_active (Boolean)          │          │ status (Enum)                │
│ is_responder (Boolean)       │          │ latitude (Float)             │
│ latitude (Float, Null)       │          │ longitude (Float)            │
│ longitude (Float, Null)      │          │ affected_radius_meters (Flt) │
│ location_updated_at (DT)     │          │ confidence_score (Float)     │
│ created_at, updated_at       │          │ corroboration_count (Int)    │
└──────────────┬───────────────┘          │ confirmed_at (DT, Null)      │
               │                          │ created_at, updated_at       │
               │                          └──────────────┬───────────────┘
               │ 1                                       │ 1
               │                                         │
               ├───────────────────┐ ┌───────────────────┤
               │                   │ │                   │
               │ *                 ▼ ▼ *                 │
┌──────────────┴───────────────┐  ┌──────────────────────┴───────────────┐
│       EmergencyReport        │  │                Alert                 │
├──────────────────────────────┤  ├──────────────────────────────────────┤
│ id (UUID, PK)                │  │ id (UUID, PK)                        │
│ user_id (FK -> User)         │  │ incident_id (FK -> Incident)         │
│ incident_id (FK -> Incident) │  │ user_id (FK -> User)                 │
│ emergency_type (Enum)        │  │ title (String)                       │
│ description (Text)           │  │ message (Text)                       │
│ severity (Enum)              │  │ severity (Enum)                      │
│ latitude (Float)             │  │ is_read (Boolean)                    │
│ longitude (Float)            │  │ read_at (DateTime, Null)             │
│ reported_at (DateTime)       │  │ created_at (DateTime)                │
│ is_independent (Boolean)     │  └──────────────────────────────────────┘
│ confidence_contribution (Flt)│
│ photo_url (String, Null)     │
└──────────────────────────────┘
```

---

## 4. Key Algorithms & Subsystems

### 4.1 Geolocation & Haversine Distance
The platform computes great-circle distances between points on Earth using spherical trigonometry:

$$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$

Where $R = 6,371,000\text{ meters}$, $\phi$ is latitude in radians, and $\lambda$ is longitude in radians. This provides sub-meter precision without requiring PostGIS or native C spatial libraries.

### 4.2 Spatial & Temporal Incident Clustering
When `POST /api/v1/reports` is received:
1. Active incidents matching the reported `emergency_type` within the last 60 minutes are queried.
2. If Haversine distance from the report to an incident center is $\le$ `incident.affected_radius_meters` (default 500m):
   - The report is linked to the existing incident.
   - If the submitting user has not previously reported this incident, `is_independent = True` and `incident.corroboration_count` increments.
   - If the user has already reported this incident, `is_independent = False` (prevents ballot-stuffing / sybil attacks).
3. If no matching incident is within radius:
   - A new Incident entity is spawned in `UNVERIFIED` status with initial radius 500m.

### 4.3 Deterministic Confidence Engine
The confidence score is computed as:
$$\text{Score} = \text{Base Corroboration} (0-75) + \text{Geographic Bonus} (0-15) + \text{Temporal Bonus} (0-10) + \text{Severity Bonus} (0-5)$$

Clamped strictly to $[0.0, 100.0]$. When score $\ge 25.0$ with $2+$ independent reports, status moves automatically from `UNVERIFIED` to `VERIFYING`.

### 4.4 Operational Lifecycle State Machine
```text
UNVERIFIED ──► VERIFYING ──► CONFIRMED ──► RESPONDING ──► CONTAINED ──► RESOLVED
    │              │             │              │
    └──────────────┴─────────────┴──────────────┴──────► FALSE_ALARM
```
* Status updates require `user.is_responder == True`.
* Transitions to `CONFIRMED` or `RESPONDING` invoke the Alert Dispatch pipeline.

### 4.5 Targeted Alert Dispatch Pipeline
1. Identifies the incident's center coordinate and radius.
2. Queries all active users with non-null location snapshots.
3. Evaluates Haversine distance for each user: $dist \le radius$.
4. Queries existing `Alert` records for `(incident_id, user_id)` to enforce zero duplication.
5. Emits new `Alert` records for newly affected users.

### 4.6 Google Maps Visualization Layer
* **Official Google Maps JavaScript Integration**: Utilizes `@googlemaps/js-api-loader` to dynamically bootstrap Google Maps in React without brittle inline script injection.
* **Theming & Map Styling**: Custom dark palette matches the Signal emergency dashboard aesthetics.
* **Markers & InfoWindows**: Renders custom SVG pins color-coded by incident severity. Markers reveal structured InfoWindows providing emergency category, confidence tier, corroborations, and navigation actions.
* **Affected Area Rings**: Renders `google.maps.Circle` geometries representing the `affected_radius_meters` around each active incident.
* **Point-in-Time Location Pin**: Displays user snapshot position without initiating background GPS polling.
* **Non-Crashing Fallback**: If `VITE_GOOGLE_MAPS_API_KEY` is omitted or network initialization fails, the component renders an informative banner with an integrated radar canvas view.

### 4.7 Report Evidence Photo Storage Flow
```text
[ Citizen Device ]
        │  Selects JPEG/PNG/WebP (< 5MB)
        ▼
[ Client Validation ] ──► Previews thumbnail, validates MIME/size
        │  Sends multipart/form-data via POST /api/v1/reports
        ▼
[ FastAPI Endpoint ] ──► Validates 5MB limit & image magic headers
        │  Generates safe UUID filename (e.g. 5a1b...c9.jpg)
        ▼
[ Local Storage ] ──────► backend/uploads/report_photos/<uuid>.<ext>
        │  Persists photo_url in emergency_reports table
        ▼
[ Incident Detail API ] ─► Aggregates evidence_photos across contributing reports
        │  Exposes photos in IncidentDetail for responders
        ▼
[ Static File Route ] ──► GET /uploads/report_photos/<uuid>.<ext>
```
