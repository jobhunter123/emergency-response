# 🚨 Signal — Community Emergency Response Platform

> **A real-time emergency coordination platform that bridges citizen observations with authoritative first-responder workflows.**

Signal transforms isolated, noisy citizen reports into verified, actionable incident intelligence through automated spatial clustering, deterministic corroboration scoring, responder lifecycle management, and privacy-preserving targeted emergency alerting.

---

## 📌 Problem & Motivation

In acute crisis situations—such as urban fires, structural collapses, floods, or hazardous spills—emergency response systems face critical challenges:
- **Noisy, Fragmented Reports**: Citizens report from varied perspectives without correlation.
- **Verification Delays**: Responders spend precious minutes determining whether a call is genuine or an isolated false alarm.
- **Premature Escalation**: Systems that automate official alarms based on single reports risk panicking the public and dispatching limited resources to false alarms.
- **Untargeted Warning Systems**: Broadcast sirens or county-wide alerts lack local spatial context, alarming residents who are safe while failing to give precise radius guidance to those in direct danger.

---

## 💡 The Solution

**Signal** provides an evidence-based emergency coordination platform:
1. **Citizen Reporting**: Citizens report observations with category, severity, description, and location.
2. **Geographic Incident Clustering**: Reports within proximity (500m) and time window are automatically grouped.
3. **Multi-User Corroboration**: Independent reports increment corroboration; duplicate reports from the same user are recorded without inflating the score.
4. **Deterministic Confidence Engine**: A bounded (0–100) scoring algorithm dynamically updates corroboration strength based on distance, recency, and severity agreement.
5. **Responder Operational Governance**: Responders retain exclusive authority to verify, confirm, contain, and resolve incidents.
6. **Dynamic Affected Area Radius**: Computes geographic impact zones using Haversine spherical geometry.
7. **Targeted Emergency Alerts**: Automatically dispatches alerts exclusively to active users located within the affected radius when an incident reaches `CONFIRMED` or `RESPONDING`, with strict deduplication.

### 🌟 Core Innovation: Evidence-Backed Corroboration

The core philosophy of Signal is simple: **a single citizen report is never treated as confirmed ground truth.**

Instead, independent reports are spatially and temporally correlated to compute an objective confidence score. An incident with strong corroboration transitions automatically to `VERIFYING` to alert emergency services, but **only verified human responders can transition an incident to `CONFIRMED`**.

#### Why This Matters:
- **Reduces False Escalation**: Isolated or bogus reports never trigger community-wide emergency alerts.
- **Evidence-Backed Incident Confidence**: First responders arrive on-scene with corroborating witness counts, spatial dispersion data, and severity agreement metrics.
- **Prevents Premature Confirmation**: Separates community corroboration strength from official operational status.
- **Enables Hyper-Targeted Alerts**: Alarms only citizens located within the computed hazard perimeter.
- **Transparent Lifecycle Chain**: Creates an auditable chain from `Citizen Report` → `Corroboration` → `Responder Verification` → `Tactical Response` → `Containment` → `Resolution`.

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   FRONTEND (React 19 + TypeScript + Vite)              │
│  - Citizen Dashboard        - Emergency Report Modal                   │
│  - Live Interactive Map     - Responder Operations Console             │
│  - Targeted Alerts Center   - Point-in-time Geolocation Snapshot       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (Bearer JWT / CORS)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + SQLAlchemy 2.x)                 │
│  ├── /auth        : Registration, OAuth2 Login, Current User Profile   │
│  ├── /reports     : Citizen Emergency Reporting & Spatial Clustering   │
│  ├── /incidents   : Incident Queries, Detail Views & Affected Radius   │
│  ├── /alerts      : Targeted Alert Inbox & Read Acknowledgement        │
│  └── /users       : Point-in-time Location Snapshot Updates            │
├────────────────────────────────────────────────────────────────────────┤
│                           CORE ENGINE SERVICES                         │
│  ├── Geolocation Service    : Haversine spherical distance calculation │
│  ├── Clustering Engine      : Proximity & temporal clustering          │
│  ├── Confidence Engine      : Bounded 0–100 deterministic corroboration│
│  ├── Incident State Machine : Responder lifecycle transitions & guards │
│  ├── Affected Area Engine   : Radius calculation & user discovery      │
│  └── Alert Service          : Targeted generation & deduplication      │
├────────────────────────────────────────────────────────────────────────┤
│                   PERSISTENCE LAYER (SQLite + SQLAlchemy ORM)          │
│  - Users (with hashed passwords, responder flags, location snapshot)   │
│  - Incidents (with status, confidence score, affected radius)          │
│  - Emergency Reports (linked to user & incident, independence flag)    │
│  - Alerts (linked to incident & recipient user, read state)            │
└────────────────────────────────────────────────────────────────────────┘
```

### Major End-to-End API Flow

```text
Citizen A Submits Report
        │
        ▼
POST /api/v1/reports ──────► Spatial/Temporal Incident Matching
                                    │
                                    ├── If first report ──► Creates Incident (UNVERIFIED)
                                    └── If nearby report ──► Correlates to existing Incident
                                                                    │
                                                                    ▼
                                                    Confidence Engine Evaluates:
                                                    - Independent user count
                                                    - Distance to epicenter
                                                    - Temporal recency
                                                    - Severity consistency
                                                                    │
                                    If score >= 25 & 2+ reports ────▼
                                    Incident Status Advances to: VERIFYING
                                                                    │
                                                                    ▼
Authorized Responder Reviews Incident ◄─────────────────────────────┘
        │
        ▼
PATCH /api/v1/incidents/{id}/status ──► Transition to CONFIRMED
                                                │
                                                ▼
                                    Affected Area Engine Calculates:
                                    - Radius in meters (default 500m)
                                    - Scans users within perimeter
                                                │
                                                ▼
                                    Targeted Alert Engine:
                                    - Generates isolated alert for affected users
                                    - Deduplicates against previous status transitions
                                                │
                                                ▼
                        Citizens Fetch Alerts (GET /api/v1/alerts)
                        Citizens Mark Read (PATCH /api/v1/alerts/{id}/read)
                                                │
                                                ▼
Responder Advances to RESPONDING ──► CONTAINED ──► RESOLVED
```

---

## 📈 Deterministic Confidence Engine

The confidence engine calculates a mathematically deterministic score bounded strictly between **`0.0`** and **`100.0`**:

$$\text{Confidence Score} = \text{Base Corroboration} + \text{Geographic Bonus} + \text{Temporal Bonus} + \text{Severity Bonus}$$

### Scoring Breakdown

| Component | Maximum | Criteria / Tiers |
| :--- | :--- | :--- |
| **Base Corroboration** | **75.0** | 1 report: 25 pts • 2 reports: 45 pts • 3 reports: 60 pts • 4 reports: 70 pts • 5+ reports: 75 pts. Repeated reports by the same user count as 0 independent corroboration. |
| **Geographic Bonus** | **15.0** | $\le 25\%$ of radius: +15 pts • $\le 50\%$: +10 pts • $\le 100\%$: +5 pts • Outside radius: 0 pts. |
| **Temporal Bonus** | **10.0** | $\le 5$ min old: +10 pts • $\le 15$ min: +8 pts • $\le 30$ min: +5 pts • $\le 60$ min: +2 pts • $> 60$ min: 0 pts. |
| **Severity Bonus** | **5.0** | Severity agreement across independent reports $\ge 75\%$: +5 pts • $\ge 50\%$: +3 pts • $> 0\%$: +1 pt. |

### Confidence Tiers

* **`LOW`** (`0.0 – 24.9`): Preliminary, isolated report. Insufficient corroboration.
* **`MODERATE`** (`25.0 – 49.9`): Corroborating signals detected. Automatically transitions incident to `VERIFYING` when 2+ independent reports corroborate.
* **`HIGH`** (`50.0 – 74.9`): Multiple independent reports confirm location and severity.
* **`VERY_HIGH`** (`75.0 – 100.0`): Strong, multi-source community corroboration across spatial, temporal, and severity dimensions.

> **Crucial Guarantee**: Confidence reflects community corroboration strength, **never** ground truth. The algorithm will never automatically mark an incident as `CONFIRMED`.

---

## 🛡️ Responder Lifecycle Management

Only authenticated users with the `is_responder: true` role can modify operational status via `PATCH /api/v1/incidents/{incident_id}/status`. Unauthorized requests receive `403 Forbidden`.

### State Machine Transition Rules

```text
┌──────────────┐
│  UNVERIFIED  ├───────────────┐
└──────┬───────┘               │
       │                       │
       ▼                       │
┌──────────────┐               │
│  VERIFYING   ├────────┐      │
└──────┬───────┘        │      ▼
       │                ├─►┌─────────────┐
       ▼                │  │ FALSE_ALARM │ (Terminal)
┌──────────────┐        │  └─────────────┘
│  CONFIRMED   ├────────┤
└──────┬───────┘        │
       │                │
       ▼                │
┌──────────────┐        │
│  RESPONDING  ├────────┘
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  CONTAINED   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   RESOLVED   │ (Terminal)
└──────────────┘
```

* **Backward transitions** (e.g., `CONFIRMED` → `VERIFYING`) are strictly rejected with `400 Bad Request`.
* **Terminal states** (`RESOLVED`, `FALSE_ALARM`) cannot transition to any other status.
* When transitioning to `CONFIRMED`, the official `confirmed_at` timestamp is permanently recorded.

---

## 🔔 Targeted Emergency Alerts

* **Perimeter-Aware**: When an incident is `CONFIRMED` or `RESPONDING`, the backend scans active users whose last location snapshot is within the incident's `affected_radius_meters` (default: 500m).
* **Zero Duplication**: Transitioning an incident from `CONFIRMED` to `RESPONDING` does not duplicate alerts for already-notified users.
* **Recipient Isolation**: Users can only fetch and view their own alerts (`GET /api/v1/alerts`). Attempts to read another user's alert return `403 Forbidden`.
* **Read Acknowledgment**: Citizens acknowledge alerts via `PATCH /api/v1/alerts/{alert_id}/read`, setting `is_read: true` and recording `read_at`.
* **Privacy by Design**: Incident detail endpoints expose only aggregate counts (`affected_user_count`). Individual user locations, names, and contact details are never exposed to other citizens.

---

## ⚡ Quick Start & Verification

### Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Node.js 18+ (Node 20+ recommended)

### 1. Start the Backend API

```bash
cd backend
# Create virtual environment if needed
python -m venv .venv
.venv\Scripts\activate   # On Windows (or 'source .venv/bin/activate' on Linux/macOS)

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base: `http://127.0.0.1:8000`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

### 2. Start the Frontend Application

```bash
cd frontend
# Configure environment (points to http://localhost:8000)
cp .env.example .env

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
- Web Application: `http://localhost:5173`

---

### 8. Real Google Maps JavaScript Visualization
- **Official Google Maps JS API**: Embedded responsive map with dark-mode styling aligned to the Signal design system.
- **Incident Markers & Severity Pinning**: Visual pins placed at coordinates with color coding corresponding to incident severity.
- **Affected Area Circles**: Dynamic SVG/Canvas circles visualizing `affected_radius_meters` around incident epicenters.
- **Interactive InfoWindows**: Clicking any marker reveals emergency category, status, confidence tier, corroboration count, and direct link to incident details.
- **Graceful Fallback**: Operates cleanly without crashing if `VITE_GOOGLE_MAPS_API_KEY` is omitted, displaying an informative notice and integrated radar visualization.

### 9. Optional Evidence Photo Attachment
- **On-Scene Visual Evidence**: Citizens can optionally attach a photo (JPEG, PNG, WebP up to 5MB) when filing a report.
- **Validation & Safe Storage**: Strict MIME-type checking, file size enforcement, and UUID-based collision-free storage in `backend/uploads/report_photos/`.
- **Controlled Serving**: Photos served through FastAPI static route `/uploads/report_photos/<uuid>.<ext>` without arbitrary filesystem access.
- **Privacy Preserving**: Citizen identity is decoupled from uploaded photos; evidence is exposed in incident details for responder situational awareness without exposing the citizen's personal metadata.

---

## 🧪 Test Suites

### Backend Unit & Integration Tests (93 Tests)
```bash
cd backend
.venv\Scripts\pytest.exe -v
```
*Result: **93 passed** (covering auth, geolocation, clustering, corroboration, confidence scoring, responder state machine, affected area, alert dispatch, and photo uploads).*

### Frontend Typecheck & Build
```bash
cd frontend
npx tsc --noEmit
npm run build
```
*Result: **0 type errors**, production bundle built cleanly.*

---

## 📁 Repository Directory Structure

```text
emergency-response/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py      # OAuth2 JWT & DB session dependencies
│   │   │   └── routes/              # FastAPI route endpoints
│   │   │       ├── alerts.py        # Targeted alerts & mark-as-read
│   │   │       ├── auth.py          # User registration & OAuth2 login
│   │   │       ├── incidents.py     # Incident queries & status management
│   │   │       ├── reports.py       # Emergency report & photo upload endpoint
│   │   │       └── users.py         # Point-in-time location snapshots
│   │   ├── core/                    # Settings, security & JWT utilities
│   │   ├── db/                      # SQLAlchemy session & SQLite initialization
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic v2 validation & response schemas
│   │   ├── services/                # Spatial, confidence & lifecycle logic
│   │   └── main.py                  # Application entry point & static file mount
│   ├── tests/                       # 93 passing unit & integration tests
│   ├── uploads/report_photos/       # Safe UUID photo storage (.gitkeep)
│   ├── .env.example                 # Safe backend environment template
│   └── requirements.txt             # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/client.ts            # Centralized API client & FormData handler
│   │   ├── components/              # Google Maps JS view & fallback components
│   │   ├── types/api.ts             # TypeScript domain & API interfaces
│   │   ├── App.tsx                  # Core interactive application UI
│   │   ├── index.css                # Custom CSS design system tokens
│   │   └── main.tsx                 # React entry point
│   ├── .env.example                 # Safe frontend environment template
│   ├── package.json                 # Dependencies & scripts
│   ├── tsconfig.json                # TypeScript compiler config
│   └── vite.config.ts               # Vite build & plugin configuration
├── docs/
│   ├── api.md                       # Comprehensive REST API specifications
│   ├── architecture.md              # System design, data flows & algorithms
│   └── development.md               # Developer setup & testing guide
├── .gitignore                       # Multi-tier ignore configuration
└── README.md                        # Master project documentation
```

---

## 🔒 Security & Privacy Posture

* **Password Security**: Passwords hashed with bcrypt (`passlib` + `bcrypt<=4.0.1`) with salt. Never stored or logged in plaintext.
* **JWT Bearer Token Authentication**: HS256-signed tokens with expiration; required on all protected endpoints.
* **Role-Based Access Control**: Responder-only actions verified at database and route levels (`is_responder: true`).
* **Tenant / Recipient Isolation**: Emergency alerts are strictly scoped by user ID; users cannot access or alter other users' alerts.
* **Privacy Protection**: Continuous GPS tracking is forbidden. Only point-in-time snapshots are stored, and individual coordinates are never exposed in public incident payloads.
* **Photo Privacy**: Citizen identity is decoupled from uploaded photos. Evidence is exposed strictly in incident details for responder awareness.
* **CORS**: Environment-aware CORS configuration restricted to authorized frontend local development origins.

---

## ⚠️ Current Limitations & Roadmap

1. **Storage Tier**: Uses SQLite for rapid local deployment and self-contained zero-dependency testing. Production scaling will adopt PostgreSQL with PostGIS.
2. **Photo File Storage**: Uses local storage under `backend/uploads/report_photos/`. Cloud production deployments should mount an S3 or Google Cloud Storage bucket.
3. **Alert Polling**: Uses point-in-time polling for targeted alerts. Production systems can layer Server-Sent Events (SSE) or WebSockets for real-time push.

---

## 📄 License

This project is licensed under the terms of the MIT License. See [LICENSE](LICENSE) for details.
