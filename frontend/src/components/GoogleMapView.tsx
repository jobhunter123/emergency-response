/// <reference types="google.maps" />
import { useEffect, useRef, useState } from "react";
import { setOptions, importLibrary } from "@googlemaps/js-api-loader";
import { Incident, IncidentDetail as IncidentDetailType, SeverityLevel } from "../types/api";

// Dark theme map styling matching Signal design system
const darkMapStyles: google.maps.MapTypeStyle[] = [
  { elementType: "geometry", stylers: [{ color: "#1e293b" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#0f172a" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#94a3b8" }] },
  {
    featureType: "administrative.locality",
    elementType: "labels.text.fill",
    stylers: [{ color: "#cbd5e1" }],
  },
  {
    featureType: "poi",
    elementType: "labels.text.fill",
    stylers: [{ color: "#64748b" }],
  },
  {
    featureType: "poi.park",
    elementType: "geometry",
    stylers: [{ color: "#1b2a47" }],
  },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#334155" }],
  },
  {
    featureType: "road",
    elementType: "geometry.stroke",
    stylers: [{ color: "#1e293b" }],
  },
  {
    featureType: "road",
    elementType: "labels.text.fill",
    stylers: [{ color: "#cbd5e1" }],
  },
  {
    featureType: "road.highway",
    elementType: "geometry",
    stylers: [{ color: "#3b82f6" }, { lightness: -40 }],
  },
  {
    featureType: "transit",
    elementType: "geometry",
    stylers: [{ color: "#1e293b" }],
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#09101d" }],
  },
  {
    featureType: "water",
    elementType: "labels.text.fill",
    stylers: [{ color: "#475569" }],
  },
];

function getSeverityColor(severity: SeverityLevel | string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL":
      return "#ef4444"; // Red
    case "HIGH":
      return "#f97316"; // Orange
    case "MEDIUM":
    case "MODERATE":
      return "#eab308"; // Amber
    case "LOW":
      return "#22c55e"; // Green
    default:
      return "#3b82f6"; // Blue
  }
}

function createMarkerSvg(color: string, pulse = false): string {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="36" height="44" viewBox="0 0 36 44">
      <defs>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.5"/>
        </filter>
      </defs>
      <path d="M18 0C8.06 0 0 8.06 0 18c0 13.5 18 26 18 26s18-12.5 18-26c0-9.94-8.06-18-18-18z" fill="${color}" filter="url(#shadow)"/>
      <circle cx="18" cy="18" r="7" fill="#ffffff" />
      ${pulse ? `<circle cx="18" cy="18" r="11" fill="none" stroke="${color}" stroke-width="2" opacity="0.6"/>` : ""}
    </svg>
  `)}`;
}

interface GoogleMapViewProps {
  detailed?: boolean;
  incidents?: Incident[];
  selectedIncident?: Incident | IncidentDetailType | null;
  userLocation?: { latitude: number; longitude: number } | null;
  onIncident?: (id: string) => void;
  // Fallback rendering callback if API key not available
  renderFallback?: () => React.ReactNode;
}

export function GoogleMapView({
  detailed = false,
  incidents = [],
  selectedIncident = null,
  userLocation = null,
  onIncident,
  renderFallback,
}: GoogleMapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<google.maps.Map | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const circlesRef = useRef<google.maps.Circle[]>([]);

  const [hasApiKey, setHasApiKey] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState<boolean>(false);

  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  useEffect(() => {
    if (!apiKey || apiKey.trim() === "") {
      setHasApiKey(false);
      return;
    }

    setHasApiKey(true);
    setOptions({
      key: apiKey,
      v: "weekly",
    });

    Promise.all([importLibrary("maps"), importLibrary("marker")])
      .then(() => {
        if (!mapContainerRef.current) return;

        // Determine default center
        let defaultCenter = { lat: 22.5726, lng: 88.3639 }; // Default civic center
        if (selectedIncident) {
          defaultCenter = {
            lat: selectedIncident.latitude,
            lng: selectedIncident.longitude,
          };
        } else if (incidents.length > 0) {
          defaultCenter = {
            lat: incidents[0].latitude,
            lng: incidents[0].longitude,
          };
        } else if (userLocation) {
          defaultCenter = {
            lat: userLocation.latitude,
            lng: userLocation.longitude,
          };
        }

        const map = new google.maps.Map(mapContainerRef.current, {
          center: defaultCenter,
          zoom: detailed ? 15 : 13,
          styles: darkMapStyles,
          disableDefaultUI: false,
          zoomControl: true,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
          backgroundColor: "#1e293b",
        });

        mapInstanceRef.current = map;
        setMapReady(true);
      })
      .catch((err: unknown) => {
        console.warn("Google Maps API Loader Error:", err);
        setLoadError(
          "Could not initialize Google Maps. Falling back to radar canvas view."
        );
      });

    return () => {
      // Clean up markers and circles on unmount
      markersRef.current.forEach((m) => m.setMap(null));
      circlesRef.current.forEach((c) => c.setMap(null));
      markersRef.current = [];
      circlesRef.current = [];
    };
  }, [apiKey, detailed]);

  // Update markers, circles, and bounds when incidents or selection changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !mapReady) return;

    // Clear existing markers and circles
    markersRef.current.forEach((m) => m.setMap(null));
    circlesRef.current.forEach((c) => c.setMap(null));
    markersRef.current = [];
    circlesRef.current = [];

    const activeIncidents = detailed && selectedIncident
      ? [selectedIncident]
      : incidents;

    const bounds = new google.maps.LatLngBounds();

    // 1. Add Incident Markers & Affected Circles
    activeIncidents.forEach((inc) => {
      const position = { lat: inc.latitude, lng: inc.longitude };
      bounds.extend(position);

      const color = getSeverityColor(inc.severity);

      // Marker
      const marker = new google.maps.Marker({
        position,
        map,
        title: inc.title,
        icon: {
          url: createMarkerSvg(color, inc.status === "CONFIRMED" || inc.status === "RESPONDING"),
          scaledSize: new google.maps.Size(32, 40),
          anchor: new google.maps.Point(16, 40),
        },
      });

      // Affected Area Circle
      const radius = inc.affected_radius_meters || 500;
      const circle = new google.maps.Circle({
        map,
        center: position,
        radius,
        fillColor: color,
        fillOpacity: 0.18,
        strokeColor: color,
        strokeOpacity: 0.75,
        strokeWeight: 2,
      });

      // InfoWindow
      const confidenceTier = (inc as IncidentDetailType).confidence_level ||
        (inc.confidence_score >= 75 ? "VERY_HIGH" : inc.confidence_score >= 50 ? "HIGH" : inc.confidence_score >= 25 ? "MODERATE" : "LOW");

      const infoHtml = `
        <div style="color: #0f172a; font-family: sans-serif; padding: 6px; min-width: 200px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <span style="font-size: 11px; font-weight: bold; text-transform: uppercase; background: ${color}20; color: ${color}; padding: 2px 6px; border-radius: 4px;">
              ${inc.severity}
            </span>
            <span style="font-size: 11px; color: #64748b; font-weight: 600;">
              ${inc.status}
            </span>
          </div>
          <h4 style="margin: 0 0 4px 0; font-size: 14px; font-weight: 700; color: #1e293b;">
            ${inc.emergency_type} Incident
          </h4>
          <p style="margin: 0 0 8px 0; font-size: 12px; color: #475569;">
            ${inc.title || `Near ${inc.latitude.toFixed(4)}, ${inc.longitude.toFixed(4)}`}
          </p>
          <div style="font-size: 11px; color: #334155; line-height: 1.5; border-top: 1px solid #e2e8f0; padding-top: 6px; margin-bottom: 8px;">
            <div>• Confidence: <strong>${Math.round(inc.confidence_score)}% (${confidenceTier})</strong></div>
            <div>• Corroborations: <strong>${inc.corroboration_count}</strong></div>
            <div>• Affected Radius: <strong>${radius}m</strong></div>
          </div>
          <button id="view-incident-btn-${inc.id}" style="width: 100%; background: #0284c7; color: #ffffff; border: none; padding: 6px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;">
            View Incident Details →
          </button>
        </div>
      `;

      const infoWindow = new google.maps.InfoWindow({
        content: infoHtml,
      });

      marker.addListener("click", () => {
        infoWindow.open(map, marker);
        // Attach listener to button inside InfoWindow once DOM is ready
        google.maps.event.addListenerOnce(infoWindow, "domready", () => {
          const btn = document.getElementById(`view-incident-btn-${inc.id}`);
          if (btn && onIncident) {
            btn.onclick = () => onIncident(inc.id);
          }
        });
      });

      markersRef.current.push(marker);
      circlesRef.current.push(circle);
    });

    // 2. Add User Location Marker if available
    if (userLocation) {
      const userPos = { lat: userLocation.latitude, lng: userLocation.longitude };
      bounds.extend(userPos);

      const userMarker = new google.maps.Marker({
        position: userPos,
        map,
        title: "Your Location (Snapshot)",
        icon: {
          url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" fill="#3b82f6" fill-opacity="0.3"/>
              <circle cx="12" cy="12" r="5" fill="#3b82f6" stroke="#ffffff" stroke-width="2"/>
            </svg>
          `)}`,
          scaledSize: new google.maps.Size(24, 24),
          anchor: new google.maps.Point(12, 12),
        },
      });

      const userInfo = new google.maps.InfoWindow({
        content: `
          <div style="color: #0f172a; font-family: sans-serif; padding: 4px; font-size: 12px;">
            <strong>Your Location</strong>
            <p style="margin: 4px 0 0 0; color: #64748b; font-size: 11px;">
              Point-in-time snapshot (${userLocation.latitude.toFixed(4)}, ${userLocation.longitude.toFixed(4)})
            </p>
          </div>
        `,
      });

      userMarker.addListener("click", () => {
        userInfo.open(map, userMarker);
      });

      markersRef.current.push(userMarker);
    }

    // Auto-center or fit bounds
    if (activeIncidents.length === 1) {
      map.setCenter({ lat: activeIncidents[0].latitude, lng: activeIncidents[0].longitude });
      map.setZoom(detailed ? 15 : 14);
    } else if (activeIncidents.length > 1) {
      map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });
    }
  }, [incidents, selectedIncident, detailed, userLocation, mapReady, onIncident]);

  // If no API key configured or error occurred, show banner + fallback visualization
  if (!hasApiKey || loadError) {
    return (
      <div style={{ position: "relative", width: "100%", height: "100%" }}>
        <div
          style={{
            position: "absolute",
            top: "10px",
            left: "10px",
            right: "10px",
            zIndex: 10,
            background: "rgba(15, 23, 42, 0.92)",
            border: "1px solid rgba(56, 189, 248, 0.3)",
            backdropFilter: "blur(8px)",
            color: "#e2e8f0",
            padding: "8px 14px",
            borderRadius: "8px",
            fontSize: "12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ color: "#38bdf8", fontSize: "14px" }}>🗺️</span>
            <span>
              <strong>Google Maps Notice:</strong>{" "}
              {loadError
                ? loadError
                : "Google Maps API Key not detected in environment (`VITE_GOOGLE_MAPS_API_KEY`). Showing integrated radar view."}
            </span>
          </div>
          <span style={{ fontSize: "11px", color: "#94a3b8" }}>
            {incidents.length} active incidents mapped
          </span>
        </div>
        {renderFallback ? renderFallback() : null}
      </div>
    );
  }

  return (
    <div
      className={`map-view ${detailed ? "map-detailed" : ""}`}
      style={{
        position: "relative",
        width: "100%",
        minHeight: detailed ? "320px" : "420px",
        height: "100%",
        borderRadius: "16px",
        overflow: "hidden",
        border: "1px solid rgba(148, 163, 184, 0.15)",
        backgroundColor: "#1e293b",
      }}
    >
      <div
        ref={mapContainerRef}
        style={{
          width: "100%",
          height: "100%",
          minHeight: detailed ? "320px" : "420px",
        }}
      />
    </div>
  );
}
