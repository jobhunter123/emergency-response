import { FormEvent, ReactNode, useEffect, useState } from "react";
import { api, ApiError, getStoredToken } from "./api/client";
import { GoogleMapView } from "./components/GoogleMapView";
import {
  Alert,
  EmergencyType,
  Incident,
  IncidentDetail as IncidentDetailType,
  IncidentStatus,
  SeverityLevel,
  User,
} from "./types/api";

type View =
  | "Overview"
  | "Incidents"
  | "Report"
  | "Alerts"
  | "Community"
  | "My Reports"
  | "Settings"
  | "Incident Detail";

type IconName =
  | "grid"
  | "alert"
  | "plus"
  | "bell"
  | "users"
  | "file"
  | "settings"
  | "search"
  | "map"
  | "check"
  | "clock"
  | "arrow"
  | "menu"
  | "close"
  | "shield"
  | "upload"
  | "refresh"
  | "logout";

const navigation: { label: View; icon: IconName }[] = [
  { label: "Overview", icon: "grid" },
  { label: "Incidents", icon: "alert" },
  { label: "Report", icon: "plus" },
  { label: "Alerts", icon: "bell" },
  { label: "Community", icon: "users" },
  { label: "My Reports", icon: "file" },
  { label: "Settings", icon: "settings" },
];

function formatTimeAgo(dateString: string): string {
  try {
    const diff = Math.floor(
      (Date.now() - new Date(dateString).getTime()) / 1000
    );
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch {
    return "Recently";
  }
}

function getSeverityTone(severity: SeverityLevel | string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL":
    case "HIGH":
      return "red";
    case "MEDIUM":
    case "MODERATE":
      return "amber";
    case "LOW":
      return "green";
    default:
      return "blue";
  }
}

function getStatusTone(status: IncidentStatus | string): string {
  switch (status?.toUpperCase()) {
    case "CONFIRMED":
      return "red";
    case "RESPONDING":
      return "blue";
    case "CONTAINED":
    case "VERIFYING":
      return "amber";
    case "RESOLVED":
      return "green";
    case "FALSE_ALARM":
    case "UNVERIFIED":
    default:
      return "neutral";
  }
}

function formatEmergencyType(type: EmergencyType | string): string {
  switch (type?.toUpperCase()) {
    case "FIRE":
      return "Structure fire";
    case "ACCIDENT":
      return "Traffic accident";
    case "MEDICAL":
      return "Medical emergency";
    case "FLOOD":
      return "Flood hazard";
    case "EARTHQUAKE":
      return "Earthquake";
    case "STORM":
      return "Severe storm";
    case "LANDSLIDE":
      return "Landslide";
    case "MISSING_PERSON":
      return "Missing person";
    case "UNSAFE_SITUATION":
      return "Unsafe situation";
    default:
      return type || "Emergency";
  }
}

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, ReactNode> = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    alert: (
      <>
        <path d="M10.3 3.5 2.7 17a2 2 0 0 0 1.8 3h15a2 2 0 0 0 1.8-3L13.7 3.5a2 2 0 0 0-3.4 0Z" />
        <path d="M12 9v4M12 17h.01" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    bell: (
      <>
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4" />
      </>
    ),
    users: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8" />
      </>
    ),
    file: (
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
        <path d="M14 2v6h6M8 13h8M8 17h6" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
    map: (
      <>
        <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z" />
        <path d="M9 3v15M15 6v15" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
    menu: <path d="M4 7h16M4 12h16M4 17h16" />,
    close: <path d="m6 6 12 12M18 6 6 18" />,
    shield: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    upload: (
      <>
        <path d="M12 16V4M7 9l5-5 5 5" />
        <path d="M5 20h14" />
      </>
    ),
    refresh: (
      <>
        <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
        <path d="M3 3v5h5" />
        <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
        <path d="M16 16h5v5" />
      </>
    ),
    logout: (
      <>
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <polyline points="16 17 21 12 16 7" />
        <line x1="21" y1="12" x2="9" y2="12" />
      </>
    ),
  };
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

function Status({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return (
    <span className={`status status-${tone}`}>
      <span className="status-dot" />
      {children}
    </span>
  );
}

function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-title">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </header>
  );
}

function FallbackSvgMap({
  detailed = false,
  incidents = [],
  selectedIncident = null,
  onIncident,
}: {
  detailed?: boolean;
  incidents?: Incident[];
  selectedIncident?: Incident | IncidentDetailType | null;
  onIncident?: (id: string) => void;
}) {
  const [zoom, setZoom] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const displayIncidents = incidents.slice(0, 5);
  const zoomIn = () =>
    setZoom((value) => Math.min(1.6, Number((value + 0.2).toFixed(1))));
  const zoomOut = () =>
    setZoom((value) => Math.max(0.8, Number((value - 0.2).toFixed(1))));

  const activeSelected =
    displayIncidents.find((i) => i.id === selectedId) || null;

  // Generate marker positions deterministically from incident coordinates
  function getMarkerStyle(inc: Incident, index: number) {
    if (detailed) {
      return { top: "50%", left: "50%" };
    }
    const xPct = 25 + ((index * 22) % 55);
    const yPct = 30 + ((index * 19) % 45);
    return { top: `${yPct}%`, left: `${xPct}%` };
  }

  return (
    <div
      className={`map-view ${detailed ? "map-detailed" : ""}`}
      aria-label="Live incident map"
    >
      <div className="map-canvas" style={{ transform: `scale(${zoom})` }}>
        <svg
          className="map-lines"
          viewBox="0 0 800 460"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path d="M-20 98C120 70 178 156 310 111S536 30 840 83M-30 300c120-69 214-75 320-9s201 79 280 6 137-79 270-46M120-30c5 112 14 194 68 278s35 164 19 242M506-20c-24 121-18 196 53 268s77 144 59 242" />
          <path
            className="minor"
            d="M-20 193c166-8 219 29 325 1s221-67 555-39M-10 392c130-42 245-18 355 17s246-26 515-67M336-20c14 136-8 241 33 342s60 112 65 168M705-20c-61 150-45 268 22 510"
          />
        </svg>

        {detailed && <div className="affected-radius" />}

        {detailed && selectedIncident ? (
          <button
            className={`map-marker marker-main selected`}
            aria-label={`${selectedIncident.title} at ${selectedIncident.latitude.toFixed(4)}, ${selectedIncident.longitude.toFixed(4)}`}
            style={{ top: "50%", left: "50%" }}
          >
            <span />
          </button>
        ) : (
          displayIncidents.map((incident, index) => {
            const isSelected = selectedId === incident.id;
            return (
              <button
                key={incident.id}
                className={`map-marker marker-${index === 0 ? "main" : index === 1 ? "two" : "three"} ${isSelected ? "selected" : ""}`}
                style={getMarkerStyle(incident, index)}
                aria-label={`${incident.title}`}
                onClick={() => setSelectedId(incident.id)}
              >
                <span />
              </button>
            );
          })
        )}
      </div>

      {activeSelected && !detailed && (
        <div className="map-popup" role="status">
          <button
            className="map-popup-close"
            aria-label="Close incident details"
            onClick={() => setSelectedId(null)}
          >
            <Icon name="close" size={14} />
          </button>
          <Status tone={getStatusTone(activeSelected.status)}>
            {activeSelected.status}
          </Status>
          <strong>{formatEmergencyType(activeSelected.emergency_type)}</strong>
          <span>
            {activeSelected.title ||
              `Near ${activeSelected.latitude.toFixed(4)}, ${activeSelected.longitude.toFixed(4)}`}
          </span>
          <small>
            {activeSelected.corroboration_count} corroboration(s) ·{" "}
            {Math.round(activeSelected.confidence_score)}% confidence
          </small>
          {onIncident && (
            <button
              className="map-popup-action"
              onClick={() => onIncident(activeSelected.id)}
            >
              View incident <Icon name="arrow" size={13} />
            </button>
          )}
        </div>
      )}

      <div className="map-controls">
        <button aria-label="Zoom in" onClick={zoomIn} disabled={zoom >= 1.6}>
          +
        </button>
        <span aria-live="polite">{Math.round(zoom * 100)}%</span>
        <button aria-label="Zoom out" onClick={zoomOut} disabled={zoom <= 0.8}>
          −
        </button>
      </div>

      <div className="map-key">
        <span className="key-dot" />
        {detailed && selectedIncident
          ? `Affected area · ${selectedIncident.affected_radius_meters}m radius`
          : `${displayIncidents.length} active emergency incidents`}
      </div>
    </div>
  );
}

function MapView({
  detailed = false,
  incidents = [],
  selectedIncident = null,
  userLocation = null,
  onIncident,
}: {
  detailed?: boolean;
  incidents?: Incident[];
  selectedIncident?: Incident | IncidentDetailType | null;
  userLocation?: { latitude: number; longitude: number } | null;
  onIncident?: (id: string) => void;
}) {
  return (
    <GoogleMapView
      detailed={detailed}
      incidents={incidents}
      selectedIncident={selectedIncident}
      userLocation={userLocation}
      onIncident={onIncident}
      renderFallback={() => (
        <FallbackSvgMap
          detailed={detailed}
          incidents={incidents}
          selectedIncident={selectedIncident}
          onIncident={onIncident}
        />
      )}
    />
  );
}

function Confidence({
  value,
  tier,
}: {
  value: number;
  tier?: string | null;
}) {
  const rounded = Math.round(value);
  return (
    <div className="confidence">
      <div className="confidence-label">
        <span>Confidence {tier ? `(${tier})` : ""}</span>
        <strong>{rounded}%</strong>
      </div>
      <div className="confidence-track">
        <span style={{ width: `${Math.min(100, Math.max(0, rounded))}%` }} />
      </div>
    </div>
  );
}

function Overview({
  incidents,
  loading,
  currentUser,
  go,
  onSelectIncident,
}: {
  incidents: Incident[];
  loading: boolean;
  currentUser: User | null;
  go: (view: View) => void;
  onSelectIncident: (id: string) => void;
}) {
  const verifiedCount = incidents.filter(
    (i) => i.status === "CONFIRMED" || i.status === "RESPONDING"
  ).length;

  return (
    <>
      <PageTitle
        eyebrow={new Date().toLocaleDateString(undefined, {
          weekday: "long",
          month: "long",
          day: "numeric",
        })}
        title={`Welcome, ${currentUser?.full_name || currentUser?.email?.split("@")[0] || "Responder"}.`}
        description={
          currentUser?.is_responder
            ? "Responder Command Portal — Live emergency events requiring monitoring or response."
            : "Community Emergency Intelligence — Verified community reports and live situations."
        }
        action={
          <button className="primary-action" onClick={() => go("Report")}>
            <Icon name="plus" /> Report emergency
          </button>
        }
      />

      <section className="stats-row" aria-label="Local incident statistics">
        <div className="stat">
          <span>Active incidents</span>
          <strong>{incidents.length}</strong>
          <small>Current active feed</small>
        </div>
        <div className="stat">
          <span>Confirmed / Responding</span>
          <strong>{verifiedCount}</strong>
          <small>Operationally verified</small>
        </div>
        <div className="stat">
          <span>User Role</span>
          <strong>{currentUser?.is_responder ? "Responder" : "Citizen"}</strong>
          <small>{currentUser?.is_responder ? "Status update authorized" : "Reporter & observer"}</small>
        </div>
        <div className="stat">
          <span>Location</span>
          <strong>
            {currentUser?.latitude ? `${currentUser.latitude.toFixed(2)}°N` : "Not set"}
          </strong>
          <small>{currentUser?.longitude ? `${currentUser.longitude.toFixed(2)}°E` : "Snapshot pending"}</small>
        </div>
      </section>

      <div className="overview-grid">
        <section className="panel map-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">Live map</span>
              <h2>Active situation map</h2>
            </div>
            <button className="text-button" onClick={() => go("Incidents")}>
              Open list <Icon name="arrow" size={15} />
            </button>
          </div>
          <MapView
            incidents={incidents}
            userLocation={
              currentUser?.latitude && currentUser?.longitude
                ? { latitude: currentUser.latitude, longitude: currentUser.longitude }
                : null
            }
            onIncident={(id) => onSelectIncident(id)}
          />
        </section>

        <section className="panel activity-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">Recent reports</span>
              <h2>Latest incidents</h2>
            </div>
            <span className="live-indicator">
              <i /> Live
            </span>
          </div>

          <div className="activity-list">
            {loading && <p style={{ padding: "1rem" }}>Loading live incidents...</p>}
            {!loading && incidents.length === 0 && (
              <p style={{ padding: "1rem", color: "var(--muted)" }}>
                No active incidents reported. The area is currently clear.
              </p>
            )}
            {incidents.slice(0, 4).map((item) => {
              const tone = getSeverityTone(item.severity);
              return (
                <button
                  className="activity-item"
                  key={item.id}
                  onClick={() => onSelectIncident(item.id)}
                >
                  <span className={`incident-mark ${tone}`}>
                    <Icon
                      name={item.status === "RESOLVED" ? "check" : "alert"}
                      size={16}
                    />
                  </span>
                  <span className="activity-copy">
                    <strong>{formatEmergencyType(item.emergency_type)}</strong>
                    <span>{item.title}</span>
                    <small>
                      {formatTimeAgo(item.created_at)} · {Math.round(item.confidence_score)}% confidence
                    </small>
                  </span>
                  <Status tone={getStatusTone(item.status)}>{item.status}</Status>
                </button>
              );
            })}
          </div>

          <button
            className="full-text-button"
            onClick={() => go("Incidents")}
          >
            View all active incidents <Icon name="arrow" size={15} />
          </button>
        </section>
      </div>

      <aside className="safety-note">
        <Icon name="shield" size={22} />
        <div>
          <strong>Community Corroboration Engine</strong>
          <span>
            Signal calculates confidence strictly from corroborating citizen reports and responder verifications.
            Always follow instructions from emergency personnel.
          </span>
        </div>
      </aside>
    </>
  );
}

function Incidents({
  incidents,
  loading,
  error,
  go,
  onSelectIncident,
  onRefresh,
}: {
  incidents: Incident[];
  loading: boolean;
  error: string | null;
  go: (view: View) => void;
  onSelectIncident: (id: string) => void;
  onRefresh: () => void;
}) {
  const [filter, setFilter] = useState("All incidents");
  const [search, setSearch] = useState("");

  const filteredIncidents = incidents.filter((i) => {
    // Status filter
    if (filter === "Confirmed" && i.status !== "CONFIRMED") return false;
    if (filter === "Responding" && i.status !== "RESPONDING") return false;
    if (
      filter === "Unverified" &&
      i.status !== "UNVERIFIED" &&
      i.status !== "VERIFYING"
    )
      return false;
    if (filter === "Resolved" && i.status !== "RESOLVED") return false;

    // Search query
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchType = i.emergency_type.toLowerCase().includes(q);
      const matchTitle = i.title.toLowerCase().includes(q);
      const matchDesc = i.description?.toLowerCase().includes(q);
      return matchType || matchTitle || matchDesc;
    }
    return true;
  });

  return (
    <>
      <PageTitle
        eyebrow="Live intelligence"
        title="Incidents"
        description="Real-time emergency incident feed verified by corroboration and responder teams."
        action={
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button className="text-button" onClick={onRefresh} title="Refresh incidents">
              <Icon name="refresh" /> Refresh
            </button>
            <button className="primary-action" onClick={() => go("Report")}>
              <Icon name="plus" /> New report
            </button>
          </div>
        }
      />

      <div className="filter-bar">
        <label className="search">
          <Icon name="search" />
          <input
            aria-label="Search incidents"
            placeholder="Search incident title, type, or description"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <div className="filter-pills">
          {[
            "All incidents",
            "Confirmed",
            "Responding",
            "Unverified",
            "Resolved",
          ].map((item) => (
            <button
              className={filter === item ? "active" : ""}
              onClick={() => setFilter(item)}
              key={item}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div style={{ padding: "1rem", background: "#fee2e2", color: "#b91c1c", borderRadius: "8px", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      <div className="incidents-layout">
        <section className="incident-results">
          <div className="result-meta">
            <span>
              {loading
                ? "Loading incidents..."
                : `${filteredIncidents.length} incident(s) found`}
            </span>
          </div>

          {!loading && filteredIncidents.length === 0 && (
            <div style={{ padding: "2rem", textAlign: "center", color: "var(--muted)" }}>
              No incidents match your current filter.
            </div>
          )}

          {filteredIncidents.map((item) => {
            const tone = getSeverityTone(item.severity);
            return (
              <button
                className="incident-row"
                key={item.id}
                onClick={() => onSelectIncident(item.id)}
              >
                <span className={`incident-mark large ${tone}`}>
                  <Icon
                    name={item.status === "RESOLVED" ? "check" : "alert"}
                  />
                </span>
                <span className="incident-row-main">
                  <span className="incident-topline">
                    <strong>{formatEmergencyType(item.emergency_type)}</strong>
                    <Status tone={getStatusTone(item.status)}>{item.status}</Status>
                  </span>
                  <span>{item.title}</span>
                  <small>
                    Radius: {item.affected_radius_meters}m · {formatTimeAgo(item.created_at)}
                  </small>
                  <Confidence value={item.confidence_score} />
                </span>
                <span className="distance">
                  {item.corroboration_count} report(s)
                  <Icon name="arrow" size={15} />
                </span>
              </button>
            );
          })}
        </section>

        <section className="sticky-map">
          <MapView
            incidents={filteredIncidents}
            onIncident={(id) => onSelectIncident(id)}
          />
        </section>
      </div>
    </>
  );
}

function IncidentDetail({
  incidentId,
  currentUser,
  go,
  onIncidentUpdated,
}: {
  incidentId: string;
  currentUser: User | null;
  go: (view: View) => void;
  onIncidentUpdated: () => void;
}) {
  const [incident, setIncident] = useState<IncidentDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  async function loadDetail() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getIncidentDetail(incidentId);
      setIncident(data);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to load incident detail");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDetail();
  }, [incidentId]);

  async function handleStatusChange(newStatus: IncidentStatus) {
    if (!currentUser?.is_responder) {
      setStatusMessage("Only verified emergency responders can update incident operational status.");
      return;
    }
    try {
      setUpdatingStatus(true);
      setStatusMessage(null);
      const updated = await api.updateIncidentStatus(incidentId, newStatus);
      setIncident(updated);
      setStatusMessage(`Incident transitioned to ${newStatus} successfully.`);
      onIncidentUpdated();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setStatusMessage(err.detail);
      } else {
        setStatusMessage("Failed to update status");
      }
    } finally {
      setUpdatingStatus(false);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <h2>Loading incident details...</h2>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <button className="back-button" onClick={() => go("Incidents")}>
          ← Back to incidents
        </button>
        <h2 style={{ color: "#b91c1c", marginTop: "1rem" }}>{error || "Incident not found"}</h2>
      </div>
    );
  }

  const tone = getSeverityTone(incident.severity);

  // Available valid responder transitions
  const validTransitions: Record<IncidentStatus, IncidentStatus[]> = {
    UNVERIFIED: ["VERIFYING", "FALSE_ALARM"],
    VERIFYING: ["CONFIRMED", "FALSE_ALARM"],
    CONFIRMED: ["RESPONDING", "FALSE_ALARM"],
    RESPONDING: ["CONTAINED", "FALSE_ALARM"],
    CONTAINED: ["RESOLVED"],
    RESOLVED: [],
    FALSE_ALARM: [],
  };

  const nextAllowed = validTransitions[incident.status] || [];

  return (
    <>
      <button className="back-button" onClick={() => go("Incidents")}>
        ← Back to incidents
      </button>

      <PageTitle
        eyebrow={`Incident ${incident.id.slice(0, 8)} · ${incident.status}`}
        title={incident.title}
        description={`Epicenter at (${incident.latitude.toFixed(4)}, ${incident.longitude.toFixed(4)}) · Type: ${incident.emergency_type}`}
        action={<Status tone={tone}>{incident.severity} severity</Status>}
      />

      {statusMessage && (
        <div style={{ padding: "1rem", background: "#f0fdf4", color: "#166534", borderRadius: "8px", marginBottom: "1.5rem" }}>
          {statusMessage}
        </div>
      )}

      {/* Responder Operational Workflow Panel */}
      {currentUser?.is_responder && (
        <div style={{ background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "10px", padding: "1.25rem", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <div>
              <span className="section-kicker" style={{ color: "#2563eb", fontWeight: "bold" }}>
                RESPONDER COMMAND CENTER
              </span>
              <h3 style={{ margin: "0.25rem 0 0 0" }}>Update Operational Lifecycle Status</h3>
            </div>
            <Status tone={getStatusTone(incident.status)}>{incident.status}</Status>
          </div>

          <p style={{ margin: "0 0 1rem 0", fontSize: "0.9rem", color: "#475569" }}>
            Advance the incident state through official verification and containment protocols.
            Transitioning to <b>CONFIRMED</b> or <b>RESPONDING</b> automatically generates targeted alerts for citizens within the {incident.affected_radius_meters}m radius.
          </p>

          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            {nextAllowed.map((nextStatus) => (
              <button
                key={nextStatus}
                className={nextStatus === "FALSE_ALARM" ? "text-button" : "primary-action"}
                disabled={updatingStatus}
                onClick={() => handleStatusChange(nextStatus)}
                style={
                  nextStatus === "CONFIRMED"
                    ? { background: "var(--red)", borderColor: "var(--red)" }
                    : nextStatus === "RESPONDING"
                    ? { background: "var(--blue)", borderColor: "var(--blue)" }
                    : nextStatus === "RESOLVED"
                    ? { background: "var(--green)", borderColor: "var(--green)" }
                    : {}
                }
              >
                Transition to {nextStatus}
              </button>
            ))}
            {nextAllowed.length === 0 && (
              <span style={{ color: "#64748b", fontStyle: "italic" }}>
                Incident has reached final status ({incident.status}). No further transitions allowed.
              </span>
            )}
          </div>
        </div>
      )}

      <div className="detail-grid">
        <section className="detail-main">
          <MapView
            detailed
            selectedIncident={incident}
            userLocation={
              currentUser?.latitude && currentUser?.longitude
                ? { latitude: currentUser.latitude, longitude: currentUser.longitude }
                : null
            }
          />

          <div className="detail-summary">
            <div>
              <span className="section-kicker">Incident overview</span>
              <h2>{formatEmergencyType(incident.emergency_type)}</h2>
              <p>{incident.description || "No additional description provided."}</p>
            </div>
            <div className="confidence-card">
              <span>Algorithmic confidence</span>
              <strong>{Math.round(incident.confidence_score)}%</strong>
              <small>Tier: {incident.confidence_level || "EVALUATING"}</small>
              <Confidence
                value={incident.confidence_score}
                tier={incident.confidence_level}
              />
            </div>
          </div>

          {incident.evidence_photos && incident.evidence_photos.length > 0 && (
            <div className="panel" style={{ padding: "1.25rem", marginTop: "1rem" }}>
              <div className="panel-heading" style={{ marginBottom: "0.75rem" }}>
                <div>
                  <span className="section-kicker">Field evidence</span>
                  <h2>Citizen photo attachments ({incident.evidence_photos.length})</h2>
                </div>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
                  gap: "12px",
                }}
              >
                {incident.evidence_photos.map((photoPath, idx) => {
                  const fullUrl = api.getPhotoUrl(photoPath);
                  return (
                    <a
                      key={idx}
                      href={fullUrl || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Click to view full image in new tab"
                      style={{
                        position: "relative",
                        display: "block",
                        borderRadius: "10px",
                        overflow: "hidden",
                        border: "1px solid rgba(148, 163, 184, 0.25)",
                        background: "#0f172a",
                      }}
                    >
                      <img
                        src={fullUrl || ""}
                        alt={`Evidence observation ${idx + 1}`}
                        style={{
                          width: "100%",
                          height: "100px",
                          objectFit: "cover",
                          display: "block",
                        }}
                      />
                      <span
                        style={{
                          position: "absolute",
                          bottom: "4px",
                          right: "6px",
                          fontSize: "10px",
                          background: "rgba(0,0,0,0.75)",
                          color: "#f8fafc",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontWeight: 600,
                        }}
                      >
                        Photo #{idx + 1}
                      </span>
                    </a>
                  );
                })}
              </div>
            </div>
          )}

          <section className="timeline-section">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">Incident events</span>
                <h2>Lifecycle log</h2>
              </div>
            </div>
            <div className="timeline">
              <div>
                <i className="active" />
                <span>{new Date(incident.updated_at).toLocaleTimeString()}</span>
                <p>
                  <strong>Current Status: {incident.status}</strong>
                  Last operational update recorded in platform.
                </p>
              </div>
              {incident.confirmed_at && (
                <div>
                  <i />
                  <span>{new Date(incident.confirmed_at).toLocaleTimeString()}</span>
                  <p>
                    <strong>Incident officially confirmed</strong>
                    Verified by authorized responder personnel.
                  </p>
                </div>
              )}
              <div>
                <i />
                <span>{new Date(incident.created_at).toLocaleTimeString()}</span>
                <p>
                  <strong>Initial report received</strong>
                  Incident cluster created at epicenter.
                </p>
              </div>
            </div>
          </section>
        </section>

        <aside className="detail-aside">
          <div className="info-block">
            <span className="section-kicker">At a glance</span>
            <dl>
              <div>
                <dt>Status</dt>
                <dd>
                  <Status tone={getStatusTone(incident.status)}>
                    {incident.status}
                  </Status>
                </dd>
              </div>
              <div>
                <dt>Severity</dt>
                <dd>{incident.severity}</dd>
              </div>
              <div>
                <dt>Affected radius</dt>
                <dd>{incident.affected_radius_meters} meters</dd>
              </div>
              <div>
                <dt>Report count</dt>
                <dd>{incident.report_count} report(s)</dd>
              </div>
              <div>
                <dt>Potentially affected</dt>
                <dd>{incident.affected_user_count} citizen(s)</dd>
              </div>
            </dl>
          </div>

          <div className="info-block">
            <span className="section-kicker">Corroboration</span>
            <div className="evidence-count">
              <strong>{incident.corroboration_count}</strong>
              <span>independent corroborations</span>
            </div>
            <button
              className="secondary-action"
              onClick={() => go("Report")}
            >
              <Icon name="check" /> Submit report here
            </button>
          </div>

          <div className="alert-box">
            <Icon name="bell" />
            <div>
              <strong>Targeted Alert Radius</strong>
              <span>
                {incident.affected_user_count} active citizen(s) currently inside the {incident.affected_radius_meters}m sphere of impact.
              </span>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}

function Report({
  currentUser,
  go,
  onReportSubmitted,
}: {
  currentUser: User | null;
  go: (view: View) => void;
  onReportSubmitted: () => void;
}) {
  const [submitted, setSubmitted] = useState(false);
  const [submittedResult, setSubmittedResult] = useState<{
    reportId: string;
    incidentId: string;
    isCorroboration: boolean;
  } | null>(null);

  const [emergencyType, setEmergencyType] = useState<EmergencyType>("FIRE");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<SeverityLevel>("HIGH");
  const [latitude, setLatitude] = useState<number>(
    currentUser?.latitude || 22.5726
  );
  const [longitude, setLongitude] = useState<number>(
    currentUser?.longitude || 88.3639
  );
  const [submitting, setSubmitting] = useState(false);
  const [locationStatus, setLocationStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);

  function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    setPhotoError(null);
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }
    const validTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!validTypes.includes(file.type)) {
      setPhotoError("Only JPEG, PNG, or WebP images are supported.");
      e.target.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setPhotoError("Image size exceeds the 5MB limit. Please choose a smaller photo.");
      e.target.value = "";
      return;
    }
    setPhotoFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPhotoPreview(objectUrl);
  }

  function handleRemovePhoto() {
    setPhotoFile(null);
    if (photoPreview) {
      URL.revokeObjectURL(photoPreview);
    }
    setPhotoPreview(null);
    setPhotoError(null);
    const fileInput = document.getElementById("evidence-photo") as HTMLInputElement | null;
    if (fileInput) {
      fileInput.value = "";
    }
  }

  function handleUseLocation() {
    if (!navigator.geolocation) {
      setLocationStatus("Geolocation is not supported by your browser.");
      return;
    }
    setLocationStatus("Detecting your location...");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(6));
        const lon = Number(pos.coords.longitude.toFixed(6));
        setLatitude(lat);
        setLongitude(lon);
        setLocationStatus(`Location detected: ${lat}, ${lon}`);

        // Update user's point-in-time location snapshot on backend
        try {
          await api.updateLocation({ latitude: lat, longitude: lon });
        } catch {
          // Non-fatal if snapshot update encounters an issue
        }
      },
      (err) => {
        setLocationStatus(`Could not acquire location: ${err.message}. Defaulting to Civic Center.`);
      }
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);
      const res = await api.createReport({
        emergency_type: emergencyType,
        description,
        severity,
        latitude,
        longitude,
        photo: photoFile,
      });
      setSubmittedResult({
        reportId: res.report.id,
        incidentId: res.incident.id,
        isCorroboration: res.incident.corroboration_count > 1,
      });
      setSubmitted(true);
      onReportSubmitted();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to submit report. Please check connection and try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted && submittedResult) {
    return (
      <div className="success-state">
        <span className="success-icon">
          <Icon name="check" size={32} />
        </span>
        <span className="eyebrow">Report received & registered</span>
        <h1>Thank you for helping your community.</h1>
        <p>
          {submittedResult.isCorroboration
            ? "Your observation corroborated an existing active incident! Confidence score has been updated dynamically."
            : "A new incident cluster has been initiated for this emergency situation."}
        </p>
        <div className="report-id">
          Report ID: <strong>{submittedResult.reportId.slice(0, 8)}</strong>
          <br />
          Linked Incident ID: <strong>{submittedResult.incidentId.slice(0, 8)}</strong>
        </div>
        <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
          <button
            className="primary-action"
            onClick={() => go("Incidents")}
          >
            View incident map <Icon name="arrow" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="form-page">
      <PageTitle
        eyebrow="Community reporting"
        title="Report an emergency"
        description="Share what you are seeing. Accurate details help the community and emergency responders coordinate."
      />

      <div className="emergency-warning">
        <Icon name="alert" />
        <div>
          <strong>Is anyone in immediate danger?</strong>
          <span>
            Call local emergency services first. Signal assists community awareness and decision-support.
          </span>
        </div>
        <button type="button">Emergency 911 / 112</button>
      </div>

      {error && (
        <div style={{ padding: "1rem", background: "#fee2e2", color: "#b91c1c", borderRadius: "8px", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      <form className="report-form" onSubmit={handleSubmit}>
        <fieldset>
          <legend>
            <span>01</span>What is happening?
          </legend>
          <div className="field-group">
            <label htmlFor="type">Emergency category</label>
            <select
              id="type"
              required
              value={emergencyType}
              onChange={(e) => setEmergencyType(e.target.value as EmergencyType)}
            >
              <option value="FIRE">Fire or smoke</option>
              <option value="ACCIDENT">Traffic / vehicle accident</option>
              <option value="MEDICAL">Medical emergency</option>
              <option value="FLOOD">Flood or water hazard</option>
              <option value="EARTHQUAKE">Earthquake</option>
              <option value="STORM">Severe storm / cyclone</option>
              <option value="LANDSLIDE">Landslide</option>
              <option value="MISSING_PERSON">Missing person</option>
              <option value="UNSAFE_SITUATION">Unsafe situation / hazard</option>
              <option value="OTHER">Other incident</option>
            </select>
          </div>

          <div className="field-group">
            <label htmlFor="description">Describe what you observe</label>
            <textarea
              id="description"
              required
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe conditions, landmarks, smoke intensity, or whether responders are already arriving."
            />
            <small>Do not put yourself in danger to gather information.</small>
          </div>
        </fieldset>

        <fieldset>
          <legend>
            <span>02</span>Where is it?
          </legend>
          <div className="location-input">
            <div style={{ display: "flex", gap: "0.5rem", flex: 1 }}>
              <label className="field-group" style={{ flex: 1 }}>
                <span>Latitude</span>
                <input
                  type="number"
                  step="0.000001"
                  required
                  value={latitude}
                  onChange={(e) => setLatitude(parseFloat(e.target.value))}
                />
              </label>
              <label className="field-group" style={{ flex: 1 }}>
                <span>Longitude</span>
                <input
                  type="number"
                  step="0.000001"
                  required
                  value={longitude}
                  onChange={(e) => setLongitude(parseFloat(e.target.value))}
                />
              </label>
            </div>
            <button type="button" onClick={handleUseLocation}>
              <Icon name="map" /> Use my location
            </button>
          </div>
          {locationStatus && (
            <small style={{ display: "block", marginTop: "0.25rem", color: "#475569" }}>
              {locationStatus}
            </small>
          )}
        </fieldset>

        <fieldset>
          <legend>
            <span>03</span>How severe is it?
          </legend>
          <div className="severity-options">
            {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as SeverityLevel[]).map(
              (item) => (
                <button
                  type="button"
                  key={item}
                  onClick={() => setSeverity(item)}
                  className={severity === item ? `selected severity-${item.toLowerCase()}` : ""}
                >
                  <i />
                  {item}
                  <small>
                    {item === "LOW"
                      ? "Limited impact"
                      : item === "MEDIUM"
                      ? "Needs attention"
                      : item === "HIGH"
                      ? "Serious danger"
                      : "Immediate life threat"}
                  </small>
                </button>
              )
            )}
          </div>
        </fieldset>

        <fieldset>
          <legend>
            <span>04</span>Evidence Photo (Optional)
          </legend>
          <div className="field-group">
            <label htmlFor="evidence-photo">Attach on-scene photo (JPEG, PNG, WebP up to 5MB)</label>
            <input
              id="evidence-photo"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handlePhotoChange}
              style={{
                display: "block",
                padding: "0.5rem 0",
                fontSize: "0.9rem",
                color: "var(--text)",
              }}
            />
            {photoError && (
              <small style={{ color: "#ef4444", fontWeight: 600, display: "block", marginTop: "0.25rem" }}>
                {photoError}
              </small>
            )}
            {photoPreview && (
              <div
                style={{
                  marginTop: "0.75rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  padding: "0.75rem",
                  background: "var(--surface)",
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                }}
              >
                <img
                  src={photoPreview}
                  alt="Evidence preview"
                  style={{
                    width: "120px",
                    height: "80px",
                    objectFit: "cover",
                    borderRadius: "6px",
                    border: "1px solid var(--border)",
                  }}
                />
                <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                  <span style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--text)" }}>
                    {photoFile?.name}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
                    {(photoFile ? photoFile.size / 1024 / 1024 : 0).toFixed(2)} MB · {photoFile?.type}
                  </span>
                  <button
                    type="button"
                    onClick={handleRemovePhoto}
                    style={{
                      padding: "0.25rem 0.6rem",
                      fontSize: "0.75rem",
                      background: "#fee2e2",
                      color: "#b91c1c",
                      border: "1px solid #fca5a5",
                      borderRadius: "4px",
                      cursor: "pointer",
                      width: "fit-content",
                    }}
                  >
                    Remove photo
                  </button>
                </div>
              </div>
            )}
            <small style={{ display: "block", marginTop: "0.5rem", color: "var(--muted)" }}>
              Optional visual evidence to help responders evaluate on-scene conditions.
            </small>
          </div>
        </fieldset>

        <div className="form-actions">
          <span>By submitting, you confirm this emergency report is accurate.</span>
          <button className="primary-action" type="submit" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit report"} <Icon name="arrow" />
          </button>
        </div>
      </form>
    </div>
  );
}

function Alerts({
  alerts,
  loading,
  error,
  onMarkRead,
  onRefresh,
}: {
  alerts: Alert[];
  loading: boolean;
  error: string | null;
  onMarkRead: (id: string) => void;
  onRefresh: () => void;
}) {
  const [unreadOnly, setUnreadOnly] = useState(false);

  const displayedAlerts = unreadOnly
    ? alerts.filter((a) => !a.is_read)
    : alerts;

  return (
    <>
      <PageTitle
        eyebrow="Targeted Community Notifications"
        title="Emergency Alerts"
        description="Official alerts generated when incidents near your location become Confirmed or Responding."
        action={
          <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
            <label className="toggle-label">
              Unread only{" "}
              <button
                role="switch"
                aria-checked={unreadOnly}
                className={`toggle ${unreadOnly ? "on" : ""}`}
                onClick={() => setUnreadOnly(!unreadOnly)}
              >
                <span />
              </button>
            </label>
            <button className="text-button" onClick={onRefresh} title="Refresh alerts">
              <Icon name="refresh" />
            </button>
          </div>
        }
      />

      {error && (
        <div style={{ padding: "1rem", background: "#fee2e2", color: "#b91c1c", borderRadius: "8px", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {loading && <p style={{ padding: "1rem" }}>Loading alerts...</p>}

      {!loading && displayedAlerts.length === 0 && (
        <div style={{ padding: "3rem", textAlign: "center", background: "var(--paper)", borderRadius: "12px", border: "1px solid var(--line)" }}>
          <Icon name="bell" size={32} />
          <h3 style={{ marginTop: "1rem" }}>No alerts at this time</h3>
          <p style={{ color: "var(--muted)" }}>
            {unreadOnly
              ? "You have marked all your emergency alerts as read."
              : "No emergency alerts have been issued near your current location snapshot."}
          </p>
        </div>
      )}

      <div className="alerts-list">
        {displayedAlerts.map((alert) => {
          const tone = getSeverityTone(alert.severity);
          return (
            <article
              key={alert.id}
              className={`alert-item ${!alert.is_read ? "urgent" : "resolved"}`}
            >
              <div className={`alert-icon ${tone}`}>
                <Icon name={alert.is_read ? "check" : "alert"} />
              </div>
              <div className="alert-content">
                <div className="alert-meta">
                  <Status tone={tone}>{alert.severity}</Status>
                  <span>{formatTimeAgo(alert.created_at)}</span>
                  {alert.is_read ? (
                    <small style={{ color: "var(--green)" }}>Read</small>
                  ) : (
                    <small style={{ color: "var(--red)", fontWeight: "bold" }}>Unread</small>
                  )}
                </div>
                <h2>{alert.title}</h2>
                <p>{alert.message}</p>
                <div className="alert-data">
                  <span>Incident ID: <b>{alert.incident_id.slice(0, 8)}</b></span>
                  <span>Received: <b>{new Date(alert.created_at).toLocaleTimeString()}</b></span>
                </div>
              </div>
              {!alert.is_read && (
                <button
                  className="secondary-action"
                  style={{ alignSelf: "center", fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}
                  onClick={() => onMarkRead(alert.id)}
                >
                  <Icon name="check" size={14} /> Mark read
                </button>
              )}
            </article>
          );
        })}
      </div>
    </>
  );
}

function Community({ incidents }: { incidents: Incident[] }) {
  const totalCorroborations = incidents.reduce(
    (sum, i) => sum + i.corroboration_count,
    0
  );

  return (
    <>
      <PageTitle
        eyebrow="People-powered safety"
        title="Community Corroboration"
        description="A transparent look at how community observations strengthen emergency response reliability."
      />

      <section className="community-hero">
        <div>
          <span className="section-kicker">Network Strength</span>
          <h2>Independent evidence confirms realities.</h2>
          <p>
            When multiple independent neighbors report the same event, confidence scores rise and responder teams deploy rapidly.
          </p>
        </div>
        <div className="community-number">
          <strong>{totalCorroborations}</strong>
          <span>total corroborations</span>
        </div>
      </section>

      <div className="community-grid">
        <div className="community-stat">
          <span className="number">{incidents.length}</span>
          <h3>Active Incidents</h3>
          <p>Current geographically grouped clusters.</p>
        </div>
        <div className="community-stat">
          <span className="number">
            {incidents.filter((i) => i.status === "CONFIRMED" || i.status === "RESPONDING").length}
          </span>
          <h3>Verified & Responding</h3>
          <p>Incidents verified by responders.</p>
        </div>
        <div className="community-stat">
          <span className="number">
            {Math.round(
              incidents.length > 0
                ? incidents.reduce((s, i) => s + i.confidence_score, 0) / incidents.length
                : 0
            )}%
          </span>
          <h3>Average Confidence</h3>
          <p>Mean algorithmic confidence score.</p>
        </div>
      </div>
    </>
  );
}

function MyReports({
  incidents,
  go,
  onSelectIncident,
}: {
  incidents: Incident[];
  go: (view: View) => void;
  onSelectIncident: (id: string) => void;
}) {
  return (
    <>
      <PageTitle
        eyebrow="Your activity"
        title="My reports"
        description="Track emergency incidents currently active in the community platform."
        action={
          <button className="primary-action" onClick={() => go("Report")}>
            <Icon name="plus" /> New report
          </button>
        }
      />

      <div className="my-report-summary">
        <div>
          <strong>{incidents.length}</strong>
          <span>Active incidents</span>
        </div>
        <div>
          <strong>
            {incidents.filter((i) => i.status === "CONFIRMED" || i.status === "RESPONDING").length}
          </strong>
          <span>Confirmed</span>
        </div>
        <div>
          <strong>
            {incidents.reduce((s, i) => s + i.corroboration_count, 0)}
          </strong>
          <span>Corroborations</span>
        </div>
      </div>

      <section className="panel reports-table">
        <div className="table-head">
          <span>Incident</span>
          <span>Status</span>
          <span>Confidence</span>
          <span>Action</span>
        </div>
        {incidents.map((item) => {
          const tone = getSeverityTone(item.severity);
          return (
            <button
              className="table-row"
              key={item.id}
              onClick={() => onSelectIncident(item.id)}
            >
              <span>
                <i className={`tiny-mark ${tone}`} />
                <span>
                  <strong>{formatEmergencyType(item.emergency_type)}</strong>
                  <small>{item.title}</small>
                </span>
              </span>
              <span>
                <Status tone={getStatusTone(item.status)}>{item.status}</Status>
              </span>
              <span>{Math.round(item.confidence_score)}%</span>
              <Icon name="arrow" size={16} />
            </button>
          );
        })}
      </section>
    </>
  );
}

function Settings({
  currentUser,
  onLocationUpdated,
  onLogout,
}: {
  currentUser: User | null;
  onLocationUpdated: (user: User) => void;
  onLogout: () => void;
}) {
  const [updatingLoc, setUpdatingLoc] = useState(false);
  const [locMsg, setLocMsg] = useState<string | null>(null);

  function handleSnapshot() {
    if (!navigator.geolocation) {
      setLocMsg("Geolocation not supported on this device.");
      return;
    }
    setUpdatingLoc(true);
    setLocMsg("Reading position...");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(6));
        const lon = Number(pos.coords.longitude.toFixed(6));
        try {
          await api.updateLocation({ latitude: lat, longitude: lon });
          const refreshed = await api.getMe();
          onLocationUpdated(refreshed);
          setLocMsg(`Location snapshot updated to (${lat}, ${lon})!`);
        } catch {
          setLocMsg("Failed to update location on backend.");
        } finally {
          setUpdatingLoc(false);
        }
      },
      (err) => {
        setLocMsg(`Location error: ${err.message}`);
        setUpdatingLoc(false);
      }
    );
  }

  return (
    <>
      <PageTitle
        eyebrow="Account & Location Settings"
        title="Settings"
        description="Manage your profile, point-in-time location snapshot, and notifications."
      />

      <div className="settings-layout">
        <aside>
          <button className="active">Account details</button>
          <button onClick={handleSnapshot}>Update location</button>
          <button onClick={onLogout} style={{ color: "var(--red)" }}>
            Sign out
          </button>
        </aside>

        <section className="settings-panel">
          <h2>User Profile</h2>
          <p>Connected to backend FastAPI service.</p>

          <div style={{ marginBottom: "1.5rem" }}>
            <p><strong>Email:</strong> {currentUser?.email}</p>
            <p><strong>Full Name:</strong> {currentUser?.full_name || "Not provided"}</p>
            <p>
              <strong>Role:</strong>{" "}
              {currentUser?.is_responder ? (
                <Status tone="blue">Authorized Responder</Status>
              ) : (
                <Status tone="neutral">Community Citizen</Status>
              )}
            </p>
            <p>
              <strong>Current Location Snapshot:</strong>{" "}
              {currentUser?.latitude !== null && currentUser?.latitude !== undefined
                ? `${currentUser.latitude.toFixed(4)}°, ${currentUser?.longitude?.toFixed(4)}°`
                : "No location snapshot recorded"}
            </p>
            {currentUser?.location_updated_at && (
              <small style={{ color: "var(--muted)" }}>
                Last updated: {new Date(currentUser.location_updated_at).toLocaleString()}
              </small>
            )}
          </div>

          <button
            className="primary-action"
            onClick={handleSnapshot}
            disabled={updatingLoc}
          >
            <Icon name="map" /> {updatingLoc ? "Updating..." : "Update my location snapshot"}
          </button>

          {locMsg && (
            <p style={{ marginTop: "1rem", color: "#166534" }}>{locMsg}</p>
          )}

          <div style={{ marginTop: "2rem", borderTop: "1px solid var(--line)", paddingTop: "1.5rem" }}>
            <button
              className="secondary-action"
              onClick={onLogout}
              style={{ color: "var(--red)" }}
            >
              <Icon name="logout" /> Sign out of Signal
            </button>
          </div>
        </section>
      </div>
    </>
  );
}

function Login({ onLoginSuccess }: { onLoginSuccess: (user: User) => void }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("citizen1@example.com");
  const [password, setPassword] = useState("securepassword123");
  const [fullName, setFullName] = useState("Jane Citizen");
  const [phoneNumber, setPhoneNumber] = useState("+1234567890");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isRegister) {
        // Register new user
        await api.register({
          email,
          password,
          full_name: fullName,
          phone_number: phoneNumber,
        });
      }

      // Log in to obtain JWT token
      await api.login({ email, password });

      // Fetch user profile
      const user = await api.getMe();
      onLoginSuccess(user);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Unable to authenticate with server. Please verify backend is running on http://localhost:8000.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <section className="login-intro">
        <div className="login-brand">
          <span className="brand-mark">S</span>
          <strong>Signal</strong>
        </div>
        <div className="login-message">
          <span className="eyebrow">Emergency Response Platform</span>
          <h1>Clear intelligence when seconds count.</h1>
          <p>
            Connect community observers with emergency responder teams through algorithmic corroboration and targeted radius alerts.
          </p>
          <div className="login-trust">
            <span>
              <Icon name="shield" />
              <span>
                <strong>Independent corroboration</strong>
                <small>Multi-observer confidence scoring</small>
              </span>
            </span>
            <span>
              <Icon name="bell" />
              <span>
                <strong>Targeted radius alerts</strong>
                <small>Generated for confirmed events</small>
              </span>
            </span>
          </div>
        </div>
        <p className="login-footnote">
          Backend API connected to FastAPI + SQLite service.
        </p>
      </section>

      <section className="login-panel">
        <form className="login-form" onSubmit={handleSubmit}>
          <span className="eyebrow">
            {isRegister ? "Join the network" : "Welcome back"}
          </span>
          <h2>{isRegister ? "Create your account" : "Sign in to Signal"}</h2>
          <p>
            {isRegister
              ? "Register to submit reports and receive local emergency alerts."
              : "Access your local incident feed and responder tools."}
          </p>

          {error && (
            <div style={{ padding: "0.75rem", background: "#fee2e2", color: "#b91c1c", borderRadius: "6px", fontSize: "0.9rem" }}>
              {error}
            </div>
          )}

          {isRegister && (
            <>
              <label className="login-field" htmlFor="name">
                <span>Full name</span>
                <input
                  id="name"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </label>
              <label className="login-field" htmlFor="phone">
                <span>Phone number</span>
                <input
                  id="phone"
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                />
              </label>
            </>
          )}

          <label className="login-field" htmlFor="email">
            <span>Email address</span>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          <label className="login-field" htmlFor="password">
            <span>Password</span>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>

          <button
            className="primary-action login-submit"
            type="submit"
            disabled={loading}
          >
            {loading
              ? "Authenticating..."
              : isRegister
              ? "Create account"
              : "Sign in"}{" "}
            <Icon name="arrow" />
          </button>

          <div className="login-divider">
            <span>{isRegister ? "Already registered?" : "New to Signal?"}</span>
          </div>

          <button
            className="create-account"
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError(null);
            }}
          >
            {isRegister ? "Sign in to existing account" : "Create a new account"}
          </button>
        </form>
      </section>
    </div>
  );
}

export default function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [initialAuthChecking, setInitialAuthChecking] = useState(true);

  const [view, setView] = useState<View>("Overview");
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Data states
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loadingIncidents, setLoadingIncidents] = useState(false);
  const [incidentsError, setIncidentsError] = useState<string | null>(null);

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loadingAlerts, setLoadingAlerts] = useState(false);
  const [alertsError, setAlertsError] = useState<string | null>(null);

  // Check stored token and restore session on mount
  useEffect(() => {
    async function checkAuth() {
      const token = getStoredToken();
      if (!token) {
        setInitialAuthChecking(false);
        return;
      }
      try {
        const user = await api.getMe();
        setCurrentUser(user);
      } catch {
        api.logout();
        setCurrentUser(null);
      } finally {
        setInitialAuthChecking(false);
      }
    }
    checkAuth();
  }, []);

  // Fetch incidents
  async function fetchIncidents() {
    try {
      setLoadingIncidents(true);
      setIncidentsError(null);
      const data = await api.getIncidents();
      setIncidents(data);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setIncidentsError(err.detail);
      } else {
        setIncidentsError("Failed to fetch active incidents from backend.");
      }
    } finally {
      setLoadingIncidents(false);
    }
  }

  // Fetch alerts
  async function fetchAlerts() {
    if (!currentUser) return;
    try {
      setLoadingAlerts(true);
      setAlertsError(null);
      const data = await api.getAlerts();
      setAlerts(data);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setAlertsError(err.detail);
      } else {
        setAlertsError("Failed to fetch alerts from backend.");
      }
    } finally {
      setLoadingAlerts(false);
    }
  }

  // Trigger data fetch on login or view change
  useEffect(() => {
    if (currentUser) {
      fetchIncidents();
      fetchAlerts();
    }
  }, [currentUser]);

  const go = (next: View) => {
    setView(next);
    setMobileOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSelectIncident = (id: string) => {
    setSelectedIncidentId(id);
    go("Incident Detail");
  };

  const handleMarkAlertRead = async (alertId: string) => {
    try {
      const updated = await api.markAlertRead(alertId);
      setAlerts((prev) =>
        prev.map((a) => (a.id === updated.id ? updated : a))
      );
    } catch {
      // Non-fatal fallback
    }
  };

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    setView("Overview");
  };

  if (initialAuthChecking) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <h2>Connecting to Signal Emergency Platform...</h2>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <Login
        onLoginSuccess={(user) => {
          setCurrentUser(user);
          setView("Overview");
        }}
      />
    );
  }

  const unreadAlertCount = alerts.filter((a) => !a.is_read).length;

  const content =
    view === "Overview" ? (
      <Overview
        incidents={incidents}
        loading={loadingIncidents}
        currentUser={currentUser}
        go={go}
        onSelectIncident={handleSelectIncident}
      />
    ) : view === "Incidents" ? (
      <Incidents
        incidents={incidents}
        loading={loadingIncidents}
        error={incidentsError}
        go={go}
        onSelectIncident={handleSelectIncident}
        onRefresh={fetchIncidents}
      />
    ) : view === "Incident Detail" && selectedIncidentId ? (
      <IncidentDetail
        incidentId={selectedIncidentId}
        currentUser={currentUser}
        go={go}
        onIncidentUpdated={() => {
          fetchIncidents();
          fetchAlerts();
        }}
      />
    ) : view === "Report" ? (
      <Report
        currentUser={currentUser}
        go={go}
        onReportSubmitted={() => {
          fetchIncidents();
          fetchAlerts();
        }}
      />
    ) : view === "Alerts" ? (
      <Alerts
        alerts={alerts}
        loading={loadingAlerts}
        error={alertsError}
        onMarkRead={handleMarkAlertRead}
        onRefresh={fetchAlerts}
      />
    ) : view === "Community" ? (
      <Community incidents={incidents} />
    ) : view === "My Reports" ? (
      <MyReports
        incidents={incidents}
        go={go}
        onSelectIncident={handleSelectIncident}
      />
    ) : (
      <Settings
        currentUser={currentUser}
        onLocationUpdated={(u) => setCurrentUser(u)}
        onLogout={handleLogout}
      />
    );

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">S</span>
          <strong>Signal</strong>
          <button
            className="mobile-close"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <Icon name="close" />
          </button>
        </div>

        <nav>
          {navigation.map((item) => (
            <button
              key={item.label}
              onClick={() => go(item.label)}
              className={
                view === item.label ||
                (view === "Incident Detail" && item.label === "Incidents")
                  ? "active"
                  : ""
              }
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.label === "Alerts" && unreadAlertCount > 0 && (
                <em>{unreadAlertCount}</em>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="system-status">
            <i />
            <span>
              <strong>Backend connected</strong>
              <small>FastAPI + SQLite operational</small>
            </span>
          </div>
          <button
            className="profile"
            onClick={() => go("Settings")}
            title="Open account settings"
          >
            <span>
              {currentUser.full_name
                ? currentUser.full_name[0].toUpperCase()
                : currentUser.email[0].toUpperCase()}
            </span>
            <span>
              <strong>
                {currentUser.full_name || currentUser.email.split("@")[0]}
              </strong>
              <small>
                {currentUser.is_responder ? "Verified Responder" : "Community Citizen"}
              </small>
            </span>
            <Icon name="settings" size={14} />
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <button
          className="nav-scrim"
          aria-label="Close menu"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <main>
        <div className="mobile-header">
          <button
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
          >
            <Icon name="menu" />
          </button>
          <div className="brand">
            <span className="brand-mark">S</span>
            <strong>Signal</strong>
          </div>
          <button
            aria-label="Notifications"
            onClick={() => go("Alerts")}
            style={{ position: "relative" }}
          >
            <Icon name="bell" />
            {unreadAlertCount > 0 && (
              <span
                style={{
                  position: "absolute",
                  top: "2px",
                  right: "2px",
                  width: "8px",
                  height: "8px",
                  background: "var(--red)",
                  borderRadius: "50%",
                }}
              />
            )}
          </button>
        </div>

        <div className="content">{content}</div>
      </main>
    </div>
  );
}
