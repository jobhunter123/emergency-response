# 🚨 Signal — Community Emergency Response Platform

> **A mission-critical emergency coordination platform that transforms real-time citizen observations into verified, actionable incident intelligence for first responders.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.0.0-61DAFB?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3.3-3178C6?logo=typescript)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-5.0.12-646CFF?logo=vite)](https://vitejs.dev)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-199900?logo=leaflet)](https://leafletjs.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.25-D71F00)](https://www.sqlalchemy.org)
[![PostgreSQL Ready](https://img.shields.io/badge/PostgreSQL-Compatible-336791?logo=postgresql)](https://www.postgresql.org)
[![Tests Passing](https://img.shields.io/badge/Tests-93%20Passed-brightgreen)](https://github.com/jobhunter123/emergency-response)

---

## 📌 Project Overview & Problem Statement

In acute urban emergencies—such as structural fires, flash floods, gas leaks, or industrial accidents—response networks confront four systemic bottlenecks:

1. **Noisy, Fragmented Reports**: Multiple 911 calls or citizen reports flood dispatch centers with contradictory details and disparate vantage points.
2. **Verification Delays**: Responders spend critical initial minutes determining whether a call is a genuine crisis or an isolated false alarm before deploying units.
3. **Premature Escalation**: Automated broadcast alarms triggered from uncorroborated single reports cause public panic and waste emergency department resources.
4. **Untargeted Warning Systems**: Broadcast sirens or county-wide push notifications lack hyper-local spatial precision, causing alert fatigue for safe citizens while failing to deliver actionable perimeter warnings to those directly in harm's way.

### The Signal Solution

**Signal** bridges citizen observations with verified first-responder workflows. It ingests ground-level emergency reports, groups them spatially and temporally into unified incidents, scores community corroboration through a bounded mathematical algorithm, and delivers hyper-targeted alerts exclusively to citizens within the calculated hazard radius—all while preserving the responder as the ultimate authority for confirmation.

---

## 🖼️ User Interface & Portfolio Previews

> *The UI is built with React 19, TypeScript, and a high-contrast warm light design system (`--ivory`, `--paper`, `--red`, `--navy`). Replace the placeholders below with live application screenshots.*

```
+------------------------------------------------------------------------------------+
| [SCREENSHOT PLACEHOLDER: Full Application Dashboard & Interactive Leaflet Map]     |
| Shows live crisis incidents mapped across OpenStreetMap tiles with custom visual   |
| severity markers (Critical, High, Medium, Low) and affected hazard radius circles. |
+------------------------------------------------------------------------------------+
```
*(Screenshot 1: Live Interactive Incident Map & Sector Overview)*

```
+------------------------------------------------------------------------------------+
| [SCREENSHOT PLACEHOLDER: Emergency Reporting Modal with Photo Evidence]            |
| Shows citizen reporting form with category selection, GPS geolocation snapshot,   |
| description input, and optional image upload (JPEG/PNG/WebP with client preview).  |
+------------------------------------------------------------------------------------+
```
*(Screenshot 2: Citizen Incident Report Creation Modal)*

```
+------------------------------------------------------------------------------------+
| [SCREENSHOT PLACEHOLDER: Responder Operations Console & Lifecycle Transitions]     |
| Displays responder-authenticated controls, verification status badges, confidence  |
| scoring breakdown, independent witness tally, and tactical status transition buttons|
+------------------------------------------------------------------------------------+
```
*(Screenshot 3: First Responder Command Console)*

```
+------------------------------------------------------------------------------------+
| [SCREENSHOT PLACEHOLDER: Targeted Emergency Alerts & Citizen Inbox]                |
| Shows targeted warning alert banner for affected citizens within perimeter radius, |
| real-time severity tag, incident distance indicator, and read-acknowledgment button|
+------------------------------------------------------------------------------------+
```
*(Screenshot 4: Hyper-Targeted Emergency Alert Notification)*

---

## 🌟 Verified Implemented Features

Every feature listed below is verified, tested, and actively functioning within the codebase:

### 1. Citizen Emergency Reporting
- Citizen submissions with category (`FIRE`, `MEDICAL`, `POLICE`, `INFRASTRUCTURE`, `NATURAL_DISASTER`, `HAZARDOUS`), severity, description, and GPS coordinates.
- Optional photographic evidence upload (JPEG, PNG, WebP up to 5MB) stored with collision-safe UUID filenames.
- Point-in-time geolocation capture without persistent background tracking.

### 2. Spatial & Temporal Clustering Engine
- Automated grouping of incoming reports into existing active incidents within a configurable spatial radius (default: 500 meters) and time window (2 hours).
- New reports in unmonitored sectors automatically instantiate new `UNVERIFIED` incidents.

### 3. Multi-User Corroboration Engine
- Corroborates reports across distinct registered users.
- Repeat reports filed by the same user update incident notes without artificially inflating the independent corroboration count.

### 4. Deterministic Confidence Scoring (0.0 – 100.0)
- Mathematical scoring engine evaluating:
  - **Base corroboration** (up to 75 pts): Scaled by independent witness count.
  - **Spatial clustering** (up to 15 pts): Proximity to incident epicenter.
  - **Temporal recency** (up to 10 pts): Freshness of reports.
  - **Severity consistency** (up to 5 pts): Category and severity agreement.
- Categorized into confidence tiers: `LOW` (0–24.9), `MODERATE` (25–49.9), `HIGH` (50–74.9), and `VERY_HIGH` (75–100.0).
- Automatically advances incident to `VERIFYING` when confidence reaches $\ge 25.0$ and 2+ independent reports exist.

### 5. Responder Operational Governance
- Role-based operational control: Only users authenticated with `is_responder: true` can transition incident lifecycle states.
- Audited lifecycle state machine:
  $$\text{UNVERIFIED} \longrightarrow \text{VERIFYING} \longrightarrow \text{CONFIRMED} \longrightarrow \text{RESPONDING} \longrightarrow \text{CONTAINED} \longrightarrow \text{RESOLVED}$$
  *(or terminal $\text{FALSE\_ALARM}$ at any pre-resolution stage).*
- Strict backward-transition protection; terminal states cannot be re-opened.

### 6. Dynamic Affected Area Calculation
- Calculates hazard zones using Haversine spherical geometry.
- Dynamically discovers active users whose latest location snapshot falls within the affected perimeter.

### 7. Hyper-Targeted Alert Dispatch
- Automatic generation of targeted warning alerts exclusively for users located within the incident's perimeter when an incident reaches `CONFIRMED` or `RESPONDING`.
- Strict alert deduplication: transitioning from `CONFIRMED` to `RESPONDING` does not duplicate alerts for already-notified users.
- Citizen alert acknowledgment flow (`PATCH /api/v1/alerts/{id}/read`).

### 8. Interactive Leaflet + OpenStreetMap Map
- Fully decoupled from proprietary map APIs (zero Google Maps API-key requirement).
- Interactive map powered by Leaflet and React-Leaflet with OpenStreetMap cartography.
- Incident markers with custom color-coded pins based on severity level.
- Affected hazard radius visual perimeter circles drawn using exact backend coordinates and radius metrics.
- Clickable popup sheets revealing category, confidence tier, corroboration count, and direct link to incident details.

---

## 🏗️ Architecture & Technology Stack

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   FRONTEND (React 19 + TypeScript + Vite)              │
│  - Citizen Dashboard        - Emergency Report Modal (w/ Photo Upload) │
│  - Live Leaflet Map         - Responder Operations Console             │
│  - Targeted Alerts Center   - Point-in-time Geolocation Snapshot       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (Bearer JWT / Dynamic CORS)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + SQLAlchemy 2.x)                 │
│  ├── /auth        : Registration, OAuth2 Login, Current User Profile   │
│  ├── /reports     : Citizen Emergency Reporting & Spatial Clustering   │
│  ├── /incidents   : Incident Queries, Detail Views & Affected Radius   │
│  ├── /alerts      : Targeted Alert Inbox & Read Acknowledgement        │
│  ├── /users       : Point-in-time Location Snapshot Updates            │
│  └── /health      : Deployment Health & Readiness Probe                │
├────────────────────────────────────────────────────────────────────────┤
│                           CORE ENGINE SERVICES                         │
│  ├── Geolocation Service    : Haversine spherical distance calculation │
│  ├── Clustering Engine      : Proximity & temporal report grouping     │
│  ├── Confidence Engine      : Bounded 0–100 deterministic corroboration│
│  ├── Incident State Machine : Responder lifecycle transitions & guards │
│  ├── Affected Area Engine   : Radius calculation & user discovery      │
│  └── Alert Service          : Targeted generation & deduplication      │
├────────────────────────────────────────────────────────────────────────┤
│                     PERSISTENCE LAYER (SQLAlchemy ORM)                 │
│  - Development / Testing   : SQLite (Fast, zero-dependency)           │
│  - Cloud Production Ready  : PostgreSQL (Render, Supabase, Neon)       │
└────────────────────────────────────────────────────────────────────────┘
```

### Technology Breakdown

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Frontend UI** | React 19, TypeScript, Vite | Fast, typed, reactive single-page client |
| **Mapping** | Leaflet 1.9, React-Leaflet, OpenStreetMap | Open-source geospatial visualization without API keys |
| **Styling** | Vanilla CSS Design Tokens, Lucide React Icons | High-contrast emergency response theme |
| **Backend API** | FastAPI, Starlette, Pydantic v2 | High-throughput asynchronous REST API |
| **Security** | OAuth2 Bearer Tokens, PyJWT, Passlib (bcrypt) | Encrypted passwords and scoped authorization |
| **ORM & Database** | SQLAlchemy 2.0, SQLite (Dev), PostgreSQL (Prod via psycopg2) | Type-safe persistence layer with schema migrations |
| **Production Server** | Uvicorn (ASGI) | Production-grade server binding to `0.0.0.0:$PORT` |

---

## ⚙️ Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | `str` | `Signal Emergency Response Platform` | Name of the platform displayed in OpenAPI docs. |
| `ENVIRONMENT` | `str` | `development` | Deployment environment (`development` or `production`). |
| `DEBUG` | `bool` | `true` | Enables debug logging and interactive tracebacks. |
| `SECRET_KEY` | `str` | *Required* | 256-bit cryptographically secure secret for JWT tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `10080` (7 days) | Token validity window. |
| `DATABASE_URL` | `str` | `sqlite:///./emergency_response.db` | Database connection string (SQLite or PostgreSQL). |
| `CORS_ORIGINS` | `str` or `list` | `["http://localhost:5173", ...]` | Allowed CORS origins. Accepts comma-separated list or `*`. |
| `PORT` | `int` | `8000` | Port for Uvicorn server to bind to (maps to `$PORT` in cloud hosting). |
| `UPLOAD_DIR` | `str` | `uploads/report_photos` | Directory path for storing uploaded photographic evidence. |

### Frontend (`frontend/.env`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | `str` | `http://localhost:8000` | URL of the backend API. Supports root URL or `/api/v1` path. |

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Node.js 18+ (Node 20+ recommended)
- Git

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies (includes FastAPI, SQLAlchemy, psycopg2-binary, passlib)
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Start development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend is now live at:
- **API Base**: `http://127.0.0.1:8000`
- **Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
- **Health Check**: `http://127.0.0.1:8000/health`

### 2. Frontend Setup

```bash
# Navigate to frontend in a new terminal
cd frontend

# Configure environment variables
cp .env.example .env

# Install dependencies (includes React 19, Leaflet, Lucide)
npm install

# Start Vite dev server
npm run dev
```

The frontend application is now accessible at `http://localhost:5173`.

---

## 🧪 Comprehensive Test Suite

The platform includes full backend test coverage across all domain services, state machines, and API endpoints, plus strict frontend TypeScript validation.

### Backend Pytest Suite (93 Passing Tests)

```bash
cd backend
pytest -v
```

**Coverage Breakdown (93 Tests):**
- `test_auth.py` (10 tests): User registration, password hashing, JWT issue/expiry, duplicate checks.
- `test_clustering.py` (7 tests): Spatial distance thresholds, temporal clustering windows, new incident creation.
- `test_confidence.py` (12 tests): Mathematical corroboration curves, temporal degradation, severity consensus, bounds checks.
- `test_state_machine.py` (13 tests): Responder verification rules, backward transition blocks, terminal state enforcement.
- `test_affected_area.py` (6 tests): Haversine distance, perimeter user discovery, edge boundary conditions.
- `test_alerts.py` (8 tests): Targeted alert generation, deduplication guards, recipient isolation.
- `test_reports_api.py` (7 tests): Emergency report filing, category validation, spatial coordination.
- `test_incidents_api.py` (9 tests): Incident list filtering, detail schemas, responder status updates.
- `test_users_api.py` (5 tests): Location snapshot updates, authenticated profile retrieval.
- `test_report_photos.py` (7 tests): MIME validation, size limits, collision-safe UUID storage, static serving.
- `test_main_routes.py` (9 tests): Root info, health endpoint, dynamic CORS headers, static routes.

### Frontend TypeScript & Build Verification

```bash
cd frontend

# Validate TypeScript type consistency (0 errors)
npm run typecheck

# Build production bundle (Clean Vite build)
npm run build
```

---

## ☁️ Deployment Guide

Signal is architected for seamless separation of concerns: deploy the frontend single-page application to **Vercel** and the backend API to **Render** with a managed **PostgreSQL** database.

### Option 1: Frontend Deployment on Vercel

The frontend includes a pre-configured `frontend/vercel.json` rewrite file to ensure SPA client-side routing works smoothly.

1. Push your repository to GitHub.
2. Log in to [Vercel](https://vercel.com) and click **Add New Project**.
3. Import your `emergency-response` repository.
4. In the Project Configuration screen:
   - **Root Directory**: Click edit and select `frontend`.
   - **Framework Preset**: Vite (detected automatically).
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`
5. In **Environment Variables**, add:
   ```env
   VITE_API_URL=https://your-backend-service.onrender.com
   ```
6. Click **Deploy**. Vercel will build and provide your production frontend URL (e.g., `https://signal-emergency.vercel.app`).

---

### Option 2: Backend Deployment on Render

The repository includes a ready-to-use `render.yaml` Blueprint or can be configured manually as a Web Service.

#### Step A: Database Options for Cloud Deployment

Choose the database strategy that best suits your deployment:

1. **Neon Serverless PostgreSQL (Recommended — 100% Free, No Credit Card, Permanent)**:
   - Sign up at [neon.tech](https://neon.tech) (free tier with no credit card required).
   - Create a project (e.g., `signal-emergency`) and copy the connection string (`postgresql://user:pass@ep-...neon.tech/neondb?sslmode=require`).
   - Neon databases do **not** expire after 30 days, making them ideal for long-lived portfolio demonstrations.

2. **Render Native Managed PostgreSQL (30-Day Expiration)**:
   - Render offers a free PostgreSQL tier in their dashboard (**New +** → **PostgreSQL**).
   - *Note*: Render's free databases automatically expire and are deleted after **30 days**, and Render often requires billing details on file to provision native databases.

3. **Local SQLite Container Fallback (Zero Setup)**:
   - If `DATABASE_URL` is omitted, the API automatically uses SQLite on the container.
   - *Important Warning*: Render's temporary filesystem is **not durable storage**. Any local SQLite database file will be permanently wiped whenever the free instance sleeps due to inactivity, restarts, or redeploys. For durable portfolio demo data, use Neon PostgreSQL as described in Option 1.

#### Step B: Deploy the FastAPI Backend Web Service
1. In Render Dashboard, click **New +** → **Web Service** (or deploy using the repository's `render.yaml` Blueprint).
2. Connect your GitHub repository.
3. Configure the settings:
   - **Name**: `signal-emergency-api`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Instance Type / Plan**: `Free` ($0/mo)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
4. In **Environment Variables**, add:
   ```env
   PYTHON_VERSION=3.11.9
   ENVIRONMENT=production
   DEBUG=false
   SECRET_KEY=<generate-a-strong-random-64-char-hex-key>
   DATABASE_URL=<your-neon-postgresql-connection-string>
   CORS_ORIGINS=https://your-frontend-app.vercel.app
   UPLOAD_DIR=uploads/report_photos
   ```
   *(Note: The platform's `config.py` automatically normalizes `postgres://` URLs to SQLAlchemy 2.0-compliant `postgresql://` automatically, and safely falls back to SQLite if `DATABASE_URL` is omitted).*
5. Click **Create Web Service**.
6. On startup, the backend automatically initializes database tables via `init_db.py`.

---

## 🔒 Security & Data Privacy

- **Password Hashing**: Passwords hashed using bcrypt with dynamic salts. Never logged or stored in plaintext.
- **JWT Authorization**: Cryptographically signed HS256 tokens with configurable expiration windows.
- **Role-Based Access Control**: Sensitive incident transitions strictly protected by `is_responder: true` verification.
- **Data Privacy by Design**: Continuous GPS tracking is never performed. The system stores only point-in-time snapshots. Public incident details expose only aggregate statistics (`affected_user_count`), never individual citizen identities or locations.
- **Alert Isolation**: Citizen emergency alert inboxes are strictly tenant-isolated (`WHERE user_id = current_user.id`).
- **File Upload Safety**: Uploaded photos are verified for MIME content type, size-capped at 5MB, stored with randomized UUID filenames, and served strictly as static assets.
- **CORS Protection**: Starlette CORS middleware dynamically configures credentials and allowed origins based on environment settings.

---

## ⚠️ Known Limitations & Future Improvements

1. **Photo Storage Tier**: Photographic evidence is currently stored on the local filesystem (`UPLOAD_DIR`). For high-availability multi-instance deployments, integrating cloud object storage (AWS S3 or Cloudinary) via an S3 driver is the natural next step.
2. **Real-Time Push Alerts**: Alert delivery is currently polled via REST intervals. A future enhancement is layering WebSockets or Server-Sent Events (SSE) for sub-second alert broadcasting.
3. **Multi-Factor Authentication (MFA)**: Adding SMS or TOTP authentication for first responder accounts.
4. **Offline Capability**: Progressive Web App (PWA) caching for field responders operating in low-connectivity disaster zones.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
