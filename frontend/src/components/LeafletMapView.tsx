import { useEffect, useMemo, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  useMap,
  ZoomControl,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import {
  Incident,
  IncidentDetail as IncidentDetailType,
  SeverityLevel,
} from "../types/api";

// Fix default Leaflet icon paths for bundlers (e.g. Vite)
// @ts-expect-error - internal Leaflet property
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Color tokens matching the Signal light-theme design system
export function getSeverityColor(severity: SeverityLevel | string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL":
      return "#ef4444"; // Emergency red
    case "HIGH":
      return "#f97316"; // Warning orange
    case "MEDIUM":
    case "MODERATE":
      return "#f59e0b"; // Amber yellow
    case "LOW":
      return "#10b981"; // Success / low risk green
    default:
      return "#3b82f6"; // Information blue
  }
}

export function getSeverityBg(severity: SeverityLevel | string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL":
      return "rgba(239, 68, 68, 0.12)";
    case "HIGH":
      return "rgba(249, 115, 22, 0.12)";
    case "MEDIUM":
    case "MODERATE":
      return "rgba(245, 158, 11, 0.12)";
    case "LOW":
      return "rgba(16, 185, 129, 0.12)";
    default:
      return "rgba(59, 130, 246, 0.12)";
  }
}

// Coordinate validation helper
export function isValidCoordinate(lat: unknown, lng: unknown): boolean {
  if (typeof lat !== "number" || typeof lng !== "number") return false;
  if (isNaN(lat) || isNaN(lng)) return false;
  if (lat < -90 || lat > 90) return false;
  if (lng < -180 || lng > 180) return false;
  return true;
}

// Emergency type icon symbol helper for markers
function getEmergencySymbol(type: string): string {
  switch (type?.toUpperCase()) {
    case "FIRE":
      return "🔥";
    case "FLOOD":
      return "🌊";
    case "ACCIDENT":
      return "🚗";
    case "MEDICAL":
      return "⚕️";
    case "EARTHQUAKE":
      return "⚡";
    case "STORM":
      return "🌪️";
    case "LANDSLIDE":
      return "⛰️";
    case "MISSING_PERSON":
      return "🔍";
    default:
      return "⚠️";
  }
}

// Custom DivIcon generator with crisp SVG pin and severity styling
function createIncidentIcon(
  incident: Incident,
  isSelected: boolean,
  isDetailedView: boolean
): L.DivIcon {
  const color = getSeverityColor(incident.severity);
  const symbol = getEmergencySymbol(incident.emergency_type);
  const isPulsing =
    incident.severity === "CRITICAL" ||
    incident.status === "CONFIRMED" ||
    incident.status === "RESPONDING" ||
    isSelected;

  const size = isSelected || isDetailedView ? 42 : 36;
  const height = isSelected || isDetailedView ? 50 : 44;
  const pulseHtml = isPulsing
    ? `<span class="leaflet-marker-pulse" style="background-color: ${color};"></span>`
    : "";

  const html = `
    <div class="custom-incident-pin ${isSelected ? "selected-pin" : ""}" style="width: ${size}px; height: ${height}px;">
      ${pulseHtml}
      <svg width="${size}" height="${height}" viewBox="0 0 36 44" fill="none" xmlns="http://www.w3.org/2000/svg" class="pin-svg">
        <defs>
          <filter id="shadow-${incident.id}" x="-20%" y="-10%" width="140%" height="130%">
            <feDropShadow dx="0" dy="3" stdDeviation="2.5" flood-color="#25233a" flood-opacity="0.32"/>
          </filter>
        </defs>
        <path d="M18 0C8.05888 0 0 8.05888 0 18C0 30.5 18 44 18 44C18 44 36 30.5 36 18C36 8.05888 27.9411 0 18 0Z" fill="${color}" filter="url(#shadow-${incident.id})"/>
        <circle cx="18" cy="18" r="14" fill="#ffffff" />
        <circle cx="18" cy="18" r="12" fill="${color}" fill-opacity="0.14" />
      </svg>
      <span class="pin-symbol">${symbol}</span>
    </div>
  `;

  return L.divIcon({
    className: "leaflet-custom-div-icon",
    html,
    iconSize: [size, height],
    iconAnchor: [size / 2, height],
    popupAnchor: [0, -height + 6],
  });
}

// User location marker icon
function createUserLocationIcon(): L.DivIcon {
  const html = `
    <div class="user-location-marker">
      <span class="user-location-ring"></span>
      <span class="user-location-dot"></span>
    </div>
  `;

  return L.divIcon({
    className: "leaflet-user-div-icon",
    html,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
}

// Map Controller for automatic bounding and smooth centering
function MapController({
  validIncidents,
  selectedIncident,
  userLocation,
  detailed,
}: {
  validIncidents: Incident[];
  selectedIncident: Incident | IncidentDetailType | null;
  userLocation: { latitude: number; longitude: number } | null;
  detailed: boolean;
}) {
  const map = useMap();
  const hasInitializedRef = useRef(false);

  useEffect(() => {
    // Invalidate map size on mount and window resize to prevent grey tiles
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 150);

    const onResize = () => {
      map.invalidateSize();
    };
    window.addEventListener("resize", onResize);

    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", onResize);
    };
  }, [map]);

  useEffect(() => {
    if (
      selectedIncident &&
      isValidCoordinate(selectedIncident.latitude, selectedIncident.longitude)
    ) {
      map.flyTo(
        [selectedIncident.latitude, selectedIncident.longitude],
        detailed ? 15 : 14,
        { duration: hasInitializedRef.current ? 1.2 : 0 }
      );
      hasInitializedRef.current = true;
      return;
    }

    if (validIncidents.length === 1) {
      const single = validIncidents[0];
      map.flyTo([single.latitude, single.longitude], detailed ? 15 : 13, {
        duration: hasInitializedRef.current ? 0.8 : 0,
      });
      hasInitializedRef.current = true;
      return;
    }

    if (validIncidents.length > 1) {
      const bounds = L.latLngBounds(
        validIncidents.map((i) => [i.latitude, i.longitude])
      );
      if (
        userLocation &&
        isValidCoordinate(userLocation.latitude, userLocation.longitude)
      ) {
        bounds.extend([userLocation.latitude, userLocation.longitude]);
      }
      map.fitBounds(bounds, {
        padding: [45, 45],
        maxZoom: 15,
        animate: hasInitializedRef.current,
      });
      hasInitializedRef.current = true;
      return;
    }

    if (
      userLocation &&
      isValidCoordinate(userLocation.latitude, userLocation.longitude)
    ) {
      map.flyTo([userLocation.latitude, userLocation.longitude], 13, {
        duration: hasInitializedRef.current ? 0.8 : 0,
      });
      hasInitializedRef.current = true;
      return;
    }

    // Default civic fallback (Kolkata civic coordinate default matching seed data)
    if (!hasInitializedRef.current) {
      map.setView([22.5726, 88.3639], 12);
      hasInitializedRef.current = true;
    }
  }, [map, validIncidents, selectedIncident, userLocation, detailed]);

  return null;
}

export interface LeafletMapViewProps {
  detailed?: boolean;
  incidents?: Incident[];
  selectedIncident?: Incident | IncidentDetailType | null;
  userLocation?: { latitude: number; longitude: number } | null;
  loading?: boolean;
  error?: string | null;
  onIncident?: (id: string) => void;
  // Retained for backward-compatibility if caller provides fallback callback
  renderFallback?: () => React.ReactNode;
}

export function LeafletMapView({
  detailed = false,
  incidents = [],
  selectedIncident = null,
  userLocation = null,
  loading = false,
  error = null,
  onIncident,
}: LeafletMapViewProps) {
  // Filter incidents for valid numeric coordinates
  const { validIncidents, invalidCount } = useMemo(() => {
    const valid: Incident[] = [];
    let invalid = 0;

    for (const inc of incidents) {
      if (isValidCoordinate(inc.latitude, inc.longitude)) {
        valid.push(inc);
      } else {
        invalid++;
      }
    }

    return { validIncidents: valid, invalidCount: invalid };
  }, [incidents]);

  // Determine initial center
  const initialCenter: [number, number] = useMemo(() => {
    if (
      selectedIncident &&
      isValidCoordinate(selectedIncident.latitude, selectedIncident.longitude)
    ) {
      return [selectedIncident.latitude, selectedIncident.longitude];
    }
    if (validIncidents.length > 0) {
      return [validIncidents[0].latitude, validIncidents[0].longitude];
    }
    if (
      userLocation &&
      isValidCoordinate(userLocation.latitude, userLocation.longitude)
    ) {
      return [userLocation.latitude, userLocation.longitude];
    }
    return [22.5726, 88.3639]; // Default civic center
  }, [selectedIncident, validIncidents, userLocation]);

  // Determine display list
  const displayIncidents = useMemo(() => {
    if (detailed && selectedIncident) {
      return isValidCoordinate(
        selectedIncident.latitude,
        selectedIncident.longitude
      )
        ? [selectedIncident]
        : [];
    }
    return validIncidents;
  }, [detailed, selectedIncident, validIncidents]);

  return (
    <div
      className={`map-view leaflet-map-wrapper ${detailed ? "map-detailed" : ""}`}
      style={{
        position: "relative",
        width: "100%",
        minHeight: detailed ? "380px" : "410px",
        height: "100%",
        borderRadius: "14px",
        overflow: "hidden",
        border: "1px solid var(--line, #e7dfd6)",
        background: "var(--ivory, #fff8ef)",
      }}
      role="region"
      aria-label="Live emergency incident map powered by OpenStreetMap"
    >
      {/* Loading Overlay */}
      {loading && (
        <div
          className="map-overlay-banner map-loading"
          style={{
            position: "absolute",
            top: 14,
            left: 14,
            zIndex: 1000,
            background: "rgba(255, 255, 255, 0.94)",
            border: "1px solid var(--line, #e7dfd6)",
            backdropFilter: "blur(8px)",
            padding: "8px 14px",
            borderRadius: "8px",
            fontSize: "12px",
            fontWeight: 600,
            color: "var(--ink, #25233a)",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            boxShadow: "0 4px 12px rgba(37, 35, 58, 0.08)",
          }}
        >
          <span className="spinner-indicator" />
          <span>Syncing live incidents from server...</span>
        </div>
      )}

      {/* Error Notice */}
      {error && (
        <div
          className="map-overlay-banner map-error"
          style={{
            position: "absolute",
            top: 14,
            left: 14,
            right: 14,
            zIndex: 1000,
            background: "rgba(255, 240, 241, 0.96)",
            border: "1px solid #ffc8cc",
            color: "var(--red, #ff4f5e)",
            padding: "9px 14px",
            borderRadius: "8px",
            fontSize: "12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            boxShadow: "0 4px 12px rgba(255, 79, 94, 0.12)",
          }}
        >
          <span>
            <strong>Connection Notice:</strong> {error}
          </span>
        </div>
      )}

      {/* Empty State Banner */}
      {!loading && !error && validIncidents.length === 0 && (
        <div
          className="map-overlay-banner map-empty"
          style={{
            position: "absolute",
            top: 14,
            left: 14,
            zIndex: 900,
            background: "rgba(255, 255, 255, 0.95)",
            border: "1px solid var(--line, #e7dfd6)",
            backdropFilter: "blur(6px)",
            padding: "8px 14px",
            borderRadius: "8px",
            fontSize: "12px",
            color: "var(--muted, #756f82)",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            boxShadow: "0 4px 12px rgba(37, 35, 58, 0.06)",
          }}
        >
          <span style={{ fontSize: "14px" }}>🟢</span>
          <span>No active incidents reported in this sector. Area clear.</span>
        </div>
      )}

      {/* Leaflet MapContainer */}
      <MapContainer
        center={initialCenter}
        zoom={detailed ? 15 : 13}
        zoomControl={false}
        scrollWheelZoom={true}
        style={{ width: "100%", height: "100%", minHeight: detailed ? "380px" : "410px" }}
      >
        <ZoomControl position="topright" />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <MapController
          validIncidents={validIncidents}
          selectedIncident={selectedIncident}
          userLocation={userLocation}
          detailed={detailed}
        />

        {/* Affected Area Circles */}
        {displayIncidents.map((inc) => {
          const color = getSeverityColor(inc.severity);
          const detailInc = inc as IncidentDetailType;
          const radiusMeters =
            detailInc.affected_area?.radius_meters ||
            inc.affected_radius_meters ||
            500;

          return (
            <Circle
              key={`circle-${inc.id}`}
              center={[inc.latitude, inc.longitude]}
              radius={radiusMeters}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: detailed ? 0.22 : 0.16,
                weight: detailed ? 2.5 : 1.5,
                dashArray:
                  inc.status === "UNVERIFIED" ? "4, 6" : undefined,
              }}
            />
          );
        })}

        {/* Incident Markers */}
        {displayIncidents.map((inc) => {
          const isSelected = selectedIncident?.id === inc.id;
          const icon = createIncidentIcon(inc, isSelected, detailed);
          const color = getSeverityColor(inc.severity);
          const bg = getSeverityBg(inc.severity);
          const radius =
            (inc as IncidentDetailType).affected_area?.radius_meters ||
            inc.affected_radius_meters ||
            500;

          const confidenceTier =
            (inc as IncidentDetailType).confidence_level ||
            (inc.confidence_score >= 75
              ? "VERY_HIGH"
              : inc.confidence_score >= 50
                ? "HIGH"
                : inc.confidence_score >= 25
                  ? "MODERATE"
                  : "LOW");

          return (
            <Marker
              key={`marker-${inc.id}`}
              position={[inc.latitude, inc.longitude]}
              icon={icon}
              title={inc.title}
            >
              <Popup className="signal-leaflet-popup" closeButton={true}>
                <div className="incident-popup-card">
                  <div className="popup-badges">
                    <span
                      className="popup-badge severity"
                      style={{ color, backgroundColor: bg }}
                    >
                      {inc.severity}
                    </span>
                    <span className="popup-badge status">{inc.status}</span>
                  </div>

                  <h3 className="popup-title">
                    {inc.emergency_type} Incident
                  </h3>
                  <p className="popup-subtitle">
                    {inc.title ||
                      `Near ${inc.latitude.toFixed(4)}, ${inc.longitude.toFixed(4)}`}
                  </p>

                  {inc.description && (
                    <p className="popup-description">{inc.description}</p>
                  )}

                  <div className="popup-metrics">
                    <div className="metric-row">
                      <span>Coordinates:</span>
                      <strong>
                        {inc.latitude.toFixed(4)}°N, {inc.longitude.toFixed(4)}°E
                      </strong>
                    </div>
                    <div className="metric-row">
                      <span>Confidence:</span>
                      <strong>
                        {Math.round(inc.confidence_score)}% ({confidenceTier})
                      </strong>
                    </div>
                    <div className="metric-row">
                      <span>Corroborations:</span>
                      <strong>
                        {inc.corroboration_count} user report(s)
                      </strong>
                    </div>
                    <div className="metric-row">
                      <span>Affected radius:</span>
                      <strong>{radius} meters</strong>
                    </div>
                  </div>

                  {onIncident && (
                    <button
                      type="button"
                      className="popup-action-btn"
                      onClick={() => onIncident(inc.id)}
                    >
                      <span>View Incident Details</span>
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M5 12h14" />
                        <path d="m12 5 7 7-7 7" />
                      </svg>
                    </button>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* User Location Marker */}
        {userLocation &&
          isValidCoordinate(userLocation.latitude, userLocation.longitude) && (
            <Marker
              position={[userLocation.latitude, userLocation.longitude]}
              icon={createUserLocationIcon()}
              title="Your Location"
            >
              <Popup className="signal-leaflet-popup">
                <div className="user-popup-card">
                  <h4>📍 Your Location Snapshot</h4>
                  <p>
                    {userLocation.latitude.toFixed(4)}°N,{" "}
                    {userLocation.longitude.toFixed(4)}°E
                  </p>
                  <small>Point-in-time device observation</small>
                </div>
              </Popup>
            </Marker>
          )}
      </MapContainer>

      {/* Map Legend / Footer Key */}
      <div
        className="map-key"
        style={{
          position: "absolute",
          left: 14,
          bottom: 14,
          zIndex: 800,
          background: "rgba(255, 253, 248, 0.94)",
          border: "1px solid var(--line, #e7dfd6)",
          borderRadius: "8px",
          padding: "7px 12px",
          fontSize: "11px",
          fontWeight: 600,
          display: "flex",
          alignItems: "center",
          gap: "8px",
          boxShadow: "0 2px 8px rgba(37, 35, 58, 0.07)",
          backdropFilter: "blur(4px)",
        }}
      >
        <span
          className="key-dot"
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            backgroundColor:
              detailed && selectedIncident
                ? getSeverityColor(selectedIncident.severity)
                : "var(--red, #ff4f5e)",
          }}
        />
        <span>
          {detailed && selectedIncident
            ? `${selectedIncident.title} · ${
                (selectedIncident as IncidentDetailType).affected_area
                  ?.radius_meters ||
                selectedIncident.affected_radius_meters ||
                500
              }m affected radius`
            : `${validIncidents.length} active incident${
                validIncidents.length === 1 ? "" : "s"
              } mapped`}
        </span>
        {invalidCount > 0 && (
          <span
            style={{
              marginLeft: "6px",
              padding: "2px 6px",
              borderRadius: "4px",
              background: "#fff0f1",
              color: "#ff4f5e",
              fontSize: "10px",
            }}
          >
            ({invalidCount} omitted: invalid coordinates)
          </span>
        )}
      </div>
    </div>
  );
}

// Backward-compatibility alias
export { LeafletMapView as GoogleMapView };
export default LeafletMapView;
