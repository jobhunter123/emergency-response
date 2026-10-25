# Signal — Community Emergency Response Platform

> A full-stack civic emergency coordination platform that structures ground-level citizen reports into corroborated incidents, enforces first-responder operational lifecycles, and dispatches hyper-targeted safety alerts to nearby residents.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-success?logo=vercel&logoColor=white)](https://emergency-response-ten.vercel.app/)
[![API Status](https://img.shields.io/badge/API-Render%20Live-blue?logo=render&logoColor=white)](https://signal-emergency-api.onrender.com/health)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-Swagger%20Docs-009688?logo=swagger&logoColor=white)](https://signal-emergency-api.onrender.com/docs)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8.0-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

> [!WARNING]
> **Prototype Demonstration Notice**
> Signal is an open-source software prototype and engineering portfolio demonstration. It is **not** an accredited Public Safety Answering Point (PSAP), an official 911/112 dispatch system, or a certified life-safety emergency service. In an actual emergency, citizens must immediately call local emergency authorities (e.g., 911, 112, 999).

---

## Quick Links

* **Live Web Application**: [https://emergency-response-ten.vercel.app/](https://emergency-response-ten.vercel.app/)
* **Backend API Base**: [https://signal-emergency-api.onrender.com](https://signal-emergency-api.onrender.com)
* **Backend Health Probe**: [https://signal-emergency-api.onrender.com/health](https://signal-emergency-api.onrender.com/health)
* **Interactive Swagger Documentation**: [https://signal-emergency-api.onrender.com/docs](https://signal-emergency-api.onrender.com/docs)
* **ReDoc API Reference**: [https://signal-emergency-api.onrender.com/redoc](https://signal-emergency-api.onrender.com/redoc)
* **GitHub Repository**: [https://github.com/jobhunter123/emergency-response](https://github.com/jobhunter123/emergency-response)

---

## Table of Contents

- [The Problem & The Solution](#the-problem--the-solution)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Emergency Incident Lifecycle](#emergency-incident-lifecycle)
- [Deterministic Confidence Scoring](#deterministic-confidence-scoring)
- [Repository Structure](#repository-structure)
- [Local Development Setup](#local-development-setup)
- [Environment Configuration](#environment-configuration)
- [Test Suite & Quality Verification](#test-suite--quality-verification)
- [Cloud Deployment Overview](#cloud-deployment-overview)
- [Troubleshooting & Common Questions](#troubleshooting--common-questions)
- [Interface Preview & Screenshot Checklist](#interface-preview--screenshot-checklist)
- [Contributing & License](#contributing--license)

---

## The Problem & The Solution

### The Challenge
During acute urban events (structural fires, flash flooding, transportation collisions, hazardous leaks), municipal emergency infrastructure faces systemic bottlenecks:
1. **Unstructured Duplicate Reports**: Dispatch centers receive dozens of conflicting phone calls describing the same incident with vague descriptions and imprecise locations.
2. **Verification Delays**: First responders spend critical initial minutes determining whether a call is genuine or an isolated false alarm before deploying tactical units.
3. **Alert Fatigue from Broad Notifications**: County-wide broadcast sirens and mobile alerts warn safe residents miles away while failing to deliver actionable, perimeter-specific warnings to individuals directly in the hazard zone.

### The Signal Approach
**Signal** addresses this coordination gap by separating citizen observations from official operational validation:
* **Citizen Observations**: Users submit point-in-time observations with emergency categories, descriptions, coordinates, and optional photographic evidence.
* **Algorithmic Clustering**: Ingested reports are grouped into unified incidents within a spatial radius (500 meters) and temporal window (60 minutes).
* **Corroboration Scoring**: A bounded, deterministic scoring engine (0.0 to 100.0) quantifies community consensus based on independent witnesses, proximity, recency, and severity agreement.
* **Responder Governance**: Only authenticated users with `is_responder = true` can transition incidents from unverified reports to confirmed emergencies or mark false alarms.
* **Perimeter-Targeted Alerts**: Once an incident reaches `CONFIRMED` or `RESPONDING`, alerts are automatically dispatched exclusively to active users whose snapshot location sits within the hazard boundary.

---

## Key Features

### 1. Citizen Emergency Reporting
* **Structured Submissions**: Supports reports across categories: `FIRE`, `FLOOD`, `ACCIDENT`, `MEDICAL`, `EARTHQUAKE`, `STORM`, `LANDSLIDE`, `MISSING_PERSON`, `UNSAFE_SITUATION`, and `OTHER`.
* **Geolocation Capture**: Captures point-in-time coordinates (`latitude`, `longitude`) via browser geolocation APIs.
* **Photographic Evidence Upload**: Optional image attachments (JPEG, PNG, WebP up to 5 MB) validated for MIME types and saved with collision-safe UUID filenames.
* **Privacy-Conscious Design**: The system records only snapshot coordinates upon explicit user action; background tracking and continuous movement trails are never stored.

### 2. Spatial & Temporal Incident Management
* **Automated Proximity Grouping**: Incoming reports within an incident's active radius (default: 500 m) and within a 60-minute window automatically link to the existing incident rather than duplicating entries.
* **Severity Escalation**: If an incoming corroborated report indicates a higher severity (`LOW` < `MEDIUM` < `HIGH` < `CRITICAL`), the incident automatically reflects the elevated severity.
* **Independent Witness Accounting**: Re-submissions from the same user are recorded for history but do not artificially inflate the independent corroboration count.

### 3. Responder Operational Workflows
* **Role-Based Access Control**: Sensitive incident transitions require an authenticated user account with `is_responder = true`.
* **Audited Lifecycle State Machine**: Enforces a strict, forward-only operational workflow (`UNVERIFIED` → `VERIFYING` → `CONFIRMED` → `RESPONDING` → `CONTAINED` → `RESOLVED`), alongside terminal `FALSE_ALARM` disposition.
* **Confirmation Timestamps**: Accurately records when an incident was first verified (`confirmed_at`) and tracks subsequent operational updates.

### 4. Targeted Citizen Alerts
* **Perimeter Dispatch**: When an incident moves to `CONFIRMED` or `RESPONDING`, alerts are generated for users located within the incident's calculated affected area.
* **Alert Deduplication**: Users who already received an alert for an incident will not receive duplicate notifications upon subsequent responder state changes.
* **Citizen Inbox & Acknowledgment**: Affected citizens can view alert notifications (`GET /api/v1/alerts`) and acknowledge them as read (`PATCH /api/v1/alerts/{id}/read`).

### 5. Interactive Geospatial Mapping
* **Open-Source Mapping Stack**: Built with Leaflet, React-Leaflet, and OpenStreetMap raster tiles, eliminating the need for proprietary map API keys or cloud map billing.
* **Dynamic Hazard Circles**: Renders precise affected radius perimeters (`affected_radius_meters`) around incidents.
* **Severity Markers & Popups**: Severity-coded pins display incident details, confidence scores, corroboration counts, and direct links to full incident inspection views.

---

## Technology Stack

| Category | Technology | Version | Purpose in Project |
| :--- | :--- | :--- | :--- |
| **Frontend** | React | `^19.0.0` | Reactive single-page client interface |
| | TypeScript | `^5.7.0` | End-to-end typed components and API contracts |
| | Vite | `^8.0.5` | Fast build pipeline and modern ESM development server |
| | Tailwind CSS | `^4.0.0` | Utility-first styling with design system variables |
| **Mapping** | Leaflet | `^1.9.4` | Open-source interactive map engine |
| | React-Leaflet | `^5.0.0` | React bindings for Leaflet maps and layers |
| | OpenStreetMap | Cartography | High-availability open map tile layers |
| **Backend** | Python | `3.11.9` | Primary backend runtime environment |
| | FastAPI | `>=0.110.0` | High-throughput asynchronous REST API framework |
| | Starlette | Bundled | ASGI framework, routing, and CORS middleware |
| | Pydantic v2 | `>=2.0.0` | Strict request/response serialization and validation |
| | Uvicorn | `>=0.28.0` | Production ASGI web server binding to `0.0.0.0:$PORT` |
| **Security** | Python-Jose | `>=3.3.0` | Cryptographically signed HS256 JWT bearer tokens |
| | Passlib & Bcrypt | `<=4.0.1` | One-way password hashing with dynamic salts |
| **Database** | SQLAlchemy | `>=2.0.0` | Declarative ORM and connection pooling |
| | SQLite | Native | Lightweight zero-config database for local development |
| | PostgreSQL | `>=2.9.9` (psycopg2) | Production relational database (tested on Render & Neon) |
| **Deployment** | Vercel | Production | Static SPA hosting with custom routing rewrites |
| | Render | Free Tier | Managed Python web service for FastAPI backend |

---

## System Architecture

```mermaid
graph TD
    subgraph Client["Frontend Client (Vercel)"]
        UI["React 19 SPA (TypeScript)"]
        MapComp["Leaflet Map Component"]
        ApiClient["Fetch API Client (client.ts)"]
    end

    subgraph External["External Geospatial Provider"]
        OSM["OpenStreetMap Tile Server (HTTPS)"]
    end

    subgraph Backend["Backend API (Render)"]
        FastAPI["FastAPI Application (Uvicorn ASGI)"]
        Routers["API Routers<br/>(/auth, /reports, /incidents, /alerts, /users)"]

        subgraph DomainServices["Core Domain Services"]
            Clustering["Spatial & Temporal Clustering Engine (500m / 60m)"]
            Confidence["Bounded Corroboration Engine (0.0 – 100.0)"]
            StateMachine["Responder Incident State Machine"]
            Spatial["Haversine Affected Area & User Discovery"]
            AlertService["Targeted Alert Dispatch & Deduplication"]
        end
    end

    subgraph Persistence["Persistence & Storage Layer"]
        ORM["SQLAlchemy 2.0 ORM"]
        DB[("PostgreSQL / SQLite")]
        PhotoDir["Static File Storage<br/>(uploads/report_photos)"]
    end

    MapComp -->|Raster Tile Requests| OSM
    UI --> MapComp
    UI --> ApiClient
    ApiClient -->|REST API Calls (Bearer JWT)| FastAPI
    FastAPI --> Routers
    Routers --> DomainServices
    Routers --> PhotoDir
    DomainServices --> ORM
    ORM --> DB
```

---

## Emergency Incident Lifecycle

Signal enforces a strict state machine to prevent premature escalation and unauthorized operational status updates.

```mermaid
stateDiagram-v2
    [*] --> UNVERIFIED: Initial Citizen Report Filed

    UNVERIFIED --> VERIFYING: Auto (Confidence >= 25 & 2+ Reports)<br/>or Responder Action
    UNVERIFIED --> FALSE_ALARM: Responder Action

    VERIFYING --> CONFIRMED: Responder Action<br/>(Triggers Alerts)
    VERIFYING --> FALSE_ALARM: Responder Action

    CONFIRMED --> RESPONDING: Responder Action<br/>(Triggers Alerts)
    CONFIRMED --> FALSE_ALARM: Responder Action

    RESPONDING --> CONTAINED: Responder Action
    RESPONDING --> FALSE_ALARM: Responder Action

    CONTAINED --> RESOLVED: Responder Action

    RESOLVED --> [*]: Terminal State
    FALSE_ALARM --> [*]: Terminal State
```

### Lifecycle Rules Enforced in Code
1. **Initial State**: Every new incident begins in `UNVERIFIED` status with an initial corroboration count of 1.
2. **Preliminary Auto-Escalation**: If incoming independent reports cause an incident's confidence score to reach $\ge 25.0$ with at least 2 independent witnesses, the status automatically advances to `VERIFYING`. A single report cannot corroborate itself.
3. **Responder Sovereign Authority**: Transitioning an incident to `CONFIRMED`, `RESPONDING`, `CONTAINED`, `RESOLVED`, or `FALSE_ALARM` strictly requires a user account with `is_responder = true`.
4. **Alert Trigger Points**: Targeted citizen alerts are dispatched exclusively when an incident transitions to `CONFIRMED` or `RESPONDING`.
5. **Terminal Protection**: `RESOLVED` and `FALSE_ALARM` are terminal states; no further transitions are permitted once reached.

---

## Deterministic Confidence Scoring

Instead of relying on opaque or non-deterministic heuristics, Signal evaluates incoming incident corroboration through a mathematical formula bounded between `0.0` and `100.0`:

$$\text{Confidence Score} = \text{Base Corroboration} + \text{Geographic Bonus} + \text{Temporal Bonus} + \text{Severity Bonus}$$

| Component | Max Points | Evaluation Logic |
| :--- | :--- | :--- |
| **Base Corroboration** | **75.0** | Scaled strictly by independent registered reporting users: <br>• 0 reports: 0.0 pts <br>• 1 report: 25.0 pts <br>• 2 reports: 45.0 pts <br>• 3 reports: 60.0 pts <br>• 4 reports: 70.0 pts <br>• 5+ reports: 75.0 pts |
| **Geographic Proximity** | **15.0** | Distance of reports from incident epicenter relative to affected radius ($R$): <br>• $\le 25\%$ of $R$: +15.0 pts <br>• $\le 50\%$ of $R$: +10.0 pts <br>• $\le 100\%$ of $R$: +5.0 pts <br>• Outside $R$: 0.0 pts |
| **Temporal Recency** | **10.0** | Elapsed time since report submission: <br>• $\le 5$ minutes: +10.0 pts <br>• $\le 15$ minutes: +8.0 pts <br>• $\le 30$ minutes: +5.0 pts <br>• $\le 60$ minutes: +2.0 pts <br>• $> 60$ minutes: 0.0 pts |
| **Severity Agreement** | **5.0** | Consistency ratio of incoming report severity matching the incident: <br>• $\ge 75\%$ consensus: +5.0 pts <br>• $\ge 50\%$ consensus: +3.0 pts <br>• $> 0\%$ consensus: +1.0 pt <br>• $0\%$ consensus: 0.0 pts |

### Confidence Tiers
* `0.0 – 24.9`: **LOW** (Single report or uncorroborated report)
* `25.0 – 49.9`: **MODERATE** (Preliminary corroboration from multiple witnesses)
* `50.0 – 74.9`: **HIGH** (Strong geographic and temporal clustering)
* `75.0 – 100.0`: **VERY HIGH** (Extensive independent witness consensus)

---

## Repository Structure

```text
emergency-response/
├── backend/                        # FastAPI Backend Application
│   ├── app/
│   │   ├── api/                    # Route handlers and dependencies
│   │   │   ├── dependencies.py     # Auth & database injection dependencies
│   │   │   └── routes/             # REST endpoints (auth, reports, incidents, alerts, users)
│   │   ├── core/                   # Application settings and JWT security configuration
│   │   ├── db/                     # SQLAlchemy engine, session maker, and table initializers
│   │   ├── models/                 # Declarative database entities (User, Incident, EmergencyReport, Alert)
│   │   ├── schemas/                # Pydantic request/response validation models
│   │   ├── services/               # Core domain algorithms (clustering, confidence, state machine, alerts)
│   │   └── main.py                 # FastAPI application assembly, lifespan, and CORS middleware
│   ├── tests/                      # Pytest test suite (93 unit and integration tests)
│   ├── .env.example                # Example backend environment variables
│   ├── pytest.ini                  # Pytest configuration
│   └── requirements.txt            # Python package dependencies
├── docs/                           # Extended technical documentation
│   ├── api.md                      # Detailed API specification and payloads
│   ├── architecture.md             # System architecture and architectural philosophy
│   ├── development.md              # Backend development and testing instructions
│   └── screenshots/                # Application interface screenshots directory
├── frontend/                       # React 19 Single Page Application
│   ├── src/
│   │   ├── api/                    # Centralized typed HTTP client (client.ts)
│   │   ├── components/             # Reusable UI components (LeafletMapView.tsx, etc.)
│   │   ├── types/                  # TypeScript interface contracts matching backend models
│   │   ├── App.tsx                 # Main application view container and navigation
│   │   ├── index.css               # Design system tokens and Leaflet custom styling
│   │   └── main.tsx                # Client entry point
│   ├── .env.example                # Example frontend environment variables
│   ├── package.json                # Frontend package dependencies and scripts
│   ├── pnpm-lock.yaml              # Pinned frontend lockfile (pnpm v10 / v9 format)
│   ├── tsconfig.json               # TypeScript compiler configuration
│   ├── vercel.json                 # Vercel SPA client-side rewrite rules
│   └── vite.config.ts              # Vite bundler configuration
├── LICENSE                         # MIT License
├── README.md                       # Main project documentation
└── render.yaml                     # Render Infrastructure-as-Code Blueprint
```

---

## Local Development Setup

### Prerequisites
* **Python**: 3.10+ (Python 3.11 recommended)
* **Node.js**: 20+ (Node 22 recommended)
* **Package Manager**: `pnpm` (or `npm`)
* **Git**

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/jobhunter123/emergency-response.git
cd emergency-response
```

---

### Step 2: Backend Setup (FastAPI)

#### On Windows (PowerShell):
```powershell
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy example environment configuration
Copy-Item .env.example .env

# Launch development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### On Linux / macOS (Bash):
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy example environment configuration
cp .env.example .env

# Launch development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

When started, the backend is available at:
* **API Root**: `http://127.0.0.1:8000`
* **Swagger UI Documentation**: `http://127.0.0.1:8000/docs`
* **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
* **Health Check Probe**: `http://127.0.0.1:8000/health`

---

### Step 3: Frontend Setup (React + Vite)

Open a new terminal window in the project root:

```bash
# Navigate to frontend directory
cd frontend

# Copy example environment file
cp .env.example .env   # On Windows: Copy-Item .env.example .env

# Install dependencies using pnpm (or npm)
pnpm install

# Start Vite development server
pnpm run dev
```

The frontend client launches and is accessible at `http://localhost:8443` (configured default in `vite.config.ts`) or `http://localhost:5173`.

---

## Environment Configuration

Signal uses environment variables to configure database connections, secret keys, and allowed CORS origins. **Never commit actual `.env` files with secret values to source control.**

### Backend Variables (`backend/.env`)

| Variable Name | Required | Default in Local Dev | Description & Example Safe Value |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | No | `Emergency Response Platform` | Display name of the application. |
| `ENVIRONMENT` | No | `development` | Environment mode (`development` or `production`). |
| `DEBUG` | No | `True` | Enables interactive debug tracebacks. Set to `False` in production. |
| `PORT` | No | `8000` | Port for the Uvicorn server to bind to. |
| `DATABASE_URL` | No | `sqlite:///./emergency_response.db` | SQLAlchemy connection string. Accepts SQLite (`sqlite:///./emergency_response.db`) or PostgreSQL (`postgresql://user:password@host:5432/dbname`). |
| `SECRET_KEY` | **Yes** | `change-this-development-secret` | 256-bit cryptographically secure key for HS256 JWT generation (e.g. `openssl rand -hex 32`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Validity lifetime of issued JWT tokens in minutes. |
| `CORS_ORIGINS` | **Yes** | Localhost list | Allowed origins parsed by `assemble_cors_origins`. In production, set to a JSON list or comma-separated list matching frontend domains. |
| `UPLOAD_DIR` | No | `uploads/report_photos` | Directory path for storing uploaded photographic evidence. |

> [!IMPORTANT]
> **CORS Origin Configuration for Cloud Deployment**
> In production on Render, set `CORS_ORIGINS` to the exact JSON list of allowed origins without trailing slashes:
> ```json
> ["http://localhost:5173","http://localhost:8443","https://emergency-response-ten.vercel.app"]
> ```
> The backend validator in `app/core/config.py` (`assemble_cors_origins`) parses JSON list strings and verifies origins against incoming request headers. If this value does not match the Vercel domain, the browser will block API calls with `400 Bad Request: Disallowed CORS origin`.

### Frontend Variables (`frontend/.env`)

| Variable Name | Required | Default in Local Dev | Description & Example Value |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | **Yes** | `http://localhost:8000` | Backend API base URL (`http://localhost:8000` for local or `https://signal-emergency-api.onrender.com` for production). |

---

## Test Suite & Quality Verification

### Backend Pytest Suite (93 Passing Tests)
The backend test suite executes against an in-memory SQLite database and exercises every domain algorithm, state machine transition, and API endpoint:

```bash
cd backend
.venv/Scripts/python -m pytest   # On Windows
pytest                           # On Linux/macOS
```

#### Test Suite Coverage Breakdown:
* `test_auth.py` (10 tests): User registration, password hashing verification, JWT token expiration, and duplicate handling.
* `test_clustering.py` (7 tests): Spatial distance thresholds, 60-minute time windows, and multi-report grouping.
* `test_confidence.py` (10 tests): Corroboration point calculations, geographic bonuses, temporal recency, and mathematical score clamping.
* `test_incident_status.py` (14 tests): Responder role authorization, forward transitions, backward transition prevention, and terminal state checks.
* `test_affected_area.py` (5 tests): Haversine distance, perimeter user discovery, and edge coordinate cases.
* `test_alerts.py` (17 tests): Targeted alert generation, user isolation, alert acknowledgment, and deduplication.
* `test_geolocation.py` (4 tests): Haversine spherical distance calculations and radius evaluation.
* `test_health.py` (2 tests): Health check probe and system status endpoints.
* `test_incidents.py` (3 tests): Incident filtering, detail retrieval, and response payload formatting.
* `test_models.py` (9 tests): Database entity relationships, default values, and column constraints.
* `test_photo_reports.py` (9 tests): Photographic evidence MIME validation, file size limits (5MB), and static photo serving.
* `test_reports.py` (10 tests): Citizen report creation, category validations, and preliminary incident assignment.

### Frontend TypeScript Verification & Production Build
```bash
cd frontend

# Verify TypeScript type consistency (0 errors)
pnpm run typecheck

# Validate production build bundle
pnpm run build
```

---

## Cloud Deployment Overview

Signal is architected for clean separation of concerns: the static frontend SPA runs on **Vercel**, while the containerized FastAPI backend runs on **Render**.

### Frontend Deployment on Vercel
1. Import the repository `jobhunter123/emergency-response` into [Vercel](https://vercel.com).
2. Configure project settings:
   * **Root Directory**: `frontend` *(Essential: the repository is a monorepo; pointing to root will fail)*
   * **Framework Preset**: `Vite`
   * **Build Command**: `pnpm run build` (or `npm run build`)
   * **Output Directory**: `dist`
3. Add Environment Variable:
   * `VITE_API_URL` = `https://signal-emergency-api.onrender.com`
4. The client uses [frontend/vercel.json](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/emergency-response/frontend/vercel.json) to rewrite all routes to `/index.html` for client-side routing.

### Backend Deployment on Render
1. Deploy as a Web Service using the repository's [render.yaml](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/emergency-response/render.yaml) blueprint, or configure manually.
2. Configure service settings:
   * **Runtime**: `Python 3`
   * **Root Directory**: `backend`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   * **Health Check Path**: `/health`
3. Configure Environment Variables in Render:
   * `ENVIRONMENT` = `production`
   * `DEBUG` = `false`
   * `SECRET_KEY` = `<strong-random-hex-string>`
   * `DATABASE_URL` = `<postgresql-connection-string>` *(e.g. from Neon Serverless PostgreSQL or Render Managed Postgres)*
   * `CORS_ORIGINS` = `["http://localhost:5173","http://localhost:8443","https://emergency-response-ten.vercel.app"]`

---

## Troubleshooting & Common Questions

#### 1. CORS Errors (`Disallowed CORS origin`)
* **Symptom**: The browser console shows `Access to fetch at ... from origin 'https://...' has been blocked by CORS policy`.
* **Fix**: In the Render dashboard under `signal-emergency-api` > **Environment**, verify that `CORS_ORIGINS` contains the frontend domain formatted as a JSON list without trailing slashes:
  `["http://localhost:5173","http://localhost:8443","https://emergency-response-ten.vercel.app"]`.

#### 2. Backend Cold Starts on Render Free Tier
* **Symptom**: The initial request to the live frontend takes 30 to 50 seconds to display incidents or return an auth token.
* **Explanation**: On the free tier, Render automatically spins down services after 15 minutes of inactivity. The first incoming request triggers a container restart. Subsequent requests respond in milliseconds.

#### 3. Leaflet Tiles Missing or Failing to Render
* **Symptom**: Map container renders a grey background with broken tile squares.
* **Fix**: Verify internet connectivity. Leaflet requires HTTPS access to `tile.openstreetmap.org`. Ensure browser ad-blockers or corporate firewall settings are not blocking tile requests.

#### 4. Vercel Build Failure (`ERR_PNPM_OUTDATED_LOCKFILE`)
* **Symptom**: Vercel CI fails during `pnpm install` indicating the lockfile is outdated.
* **Fix**: Run `npx -y pnpm@10.34.3 install --lockfile-only` inside the `frontend/` directory, verify `git diff frontend/pnpm-lock.yaml`, and commit the updated lockfile.

---

## Interface Preview & Screenshot Checklist

### UI Architecture Previews

```text
+-----------------------------------------------------------------------------------------+
| [PREVIEW: Incident Command Overview & Leaflet Map]                                      |
| Live interactive Leaflet map displaying active urban incidents categorized by severity  |
| with color-coded pins, dynamic hazard impact circles, and quick telemetry summary cards |
+-----------------------------------------------------------------------------------------+
```
*Figure 1: Citizen & Responder Map Overview with Affected Hazard Perimeters.*

```text
+-----------------------------------------------------------------------------------------+
| [PREVIEW: Citizen Emergency Reporting Form]                                             |
| Multi-step modal capturing emergency category, severity level, description, GPS snapshot|
| coordinates, and optional photographic evidence upload with instant client preview      |
+-----------------------------------------------------------------------------------------+
```
*Figure 2: Citizen Emergency Incident Report Submission Modal.*

```text
+-----------------------------------------------------------------------------------------+
| [PREVIEW: Responder Lifecycle Operations Panel]                                         |
| Authenticated responder controls showing confidence breakdown, independent witness count|
| and state transition actions (Verify, Confirm, Respond, Contain, Resolve, False Alarm)  |
+-----------------------------------------------------------------------------------------+
```
*Figure 3: First Responder Operational State Transition Console.*

```text
+-----------------------------------------------------------------------------------------+
| [PREVIEW: Targeted Citizen Alert Inbox]                                                 |
| High-priority warning cards delivered to citizens situated within an active perimeter,  |
| providing actionable guidance, incident proximity metrics, and read-acknowledgments     |
+-----------------------------------------------------------------------------------------+
```
*Figure 4: Hyper-Targeted Emergency Alert Notification Center.*

---

### Screenshot Capture Checklist

To add authentic application screenshots to the repository without exposing personal credentials, capture real screens from the running application and save them to `docs/screenshots/`:

| Screen | Target File Path | What to Showcase |
| :--- | :--- | :--- |
| **1. Overview & Map** | `docs/screenshots/01-dashboard-map.png` | Live Leaflet map with active incident pins, affected radius circles, and incident sidebar. |
| **2. Reporting Modal** | `docs/screenshots/02-reporting-form.png` | Citizen reporting modal with category selection, description, coordinate pin, and photo dropzone. |
| **3. Responder Console** | `docs/screenshots/03-responder-console.png` | Incident detail view showing lifecycle transition buttons (`Confirm`, `Respond`, `Contain`, `Resolve`), confidence breakdown, and corroboration tally. |
| **4. Targeted Alerts** | `docs/screenshots/04-targeted-alerts.png` | Citizen alert inbox displaying targeted radius warning cards with distance tags and read-acknowledgment buttons. |

#### Manual Capture Instructions:
1. Open [https://emergency-response-ten.vercel.app/](https://emergency-response-ten.vercel.app/) in Google Chrome or Microsoft Edge.
2. Sign in using the pre-seeded demo citizen account (`citizen1@example.com` / `securepassword123`).
3. Press `F12` to open Developer Tools, then press `Ctrl + Shift + P` (or `Cmd + Shift + P` on macOS).
4. Type `Capture full size screenshot` (or `Capture screenshot` with viewport set to 1440 × 900).
5. Save the image into `docs/screenshots/` matching the filenames above.
6. Replace the ASCII preview blocks with:
   ```markdown
   ![Signal Dashboard](docs/screenshots/01-dashboard-map.png)
   ![Citizen Reporting](docs/screenshots/02-reporting-form.png)
   ![Responder Console](docs/screenshots/03-responder-console.png)
   ![Targeted Alerts](docs/screenshots/04-targeted-alerts.png)
   ```

---

## Contributing & License

### Contributing
Contributions to improve platform resilience, add test scenarios, or extend domain algorithms are welcome.

1. Fork the repository [https://github.com/jobhunter123/emergency-response](https://github.com/jobhunter123/emergency-response).
2. Create a feature branch (`git checkout -b feature/improved-clustering`).
3. Ensure all tests pass:
   ```bash
   cd backend && pytest
   cd ../frontend && pnpm run typecheck && pnpm run build
   ```
4. Commit your changes with descriptive messages (`git commit -m 'feat: add spatial index support'`).
5. Push to your branch and open a Pull Request.

### Extended Documentation
* [API Specification & Endpoints](docs/api.md)
* [System Architecture & Design Decisions](docs/architecture.md)
* [Backend Development Guide](docs/development.md)

### License
This project is open-source software licensed under the [MIT License](LICENSE).

### Acknowledgements
* [FastAPI](https://fastapi.tiangolo.com/) by Sebastián Ramírez for asynchronous Python web services.
* [Leaflet](https://leafletjs.com/) and [React-Leaflet](https://react-leaflet.js.org/) for open-source geospatial visualization.
* [OpenStreetMap](https://www.openstreetmap.org/) contributors for open geospatial cartography.
* [Vite](https://vitejs.dev/) and [React](https://react.dev/) for client development tooling.
