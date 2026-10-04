/**
 * Centralized API client service layer for the Emergency Response Platform.
 * Interacts with FastAPI backend using standard fetch and JSON serialization.
 */

import {
  Alert,
  AuthToken,
  EmergencyReportCreate,
  EmergencyReportResponse,
  EmergencyReportSubmissionResponse,
  Incident,
  IncidentDetail,
  IncidentStatus,
  User,
  UserLocationResponse,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const API_V1_PREFIX = `${API_BASE_URL}/api/v1`;

const TOKEN_STORAGE_KEY = "signal_auth_token";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore storage quota or disabled storage errors
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_V1_PREFIX}${endpoint}`;
  const token = getStoredToken();

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch (err) {
    throw new ApiError(
      0,
      `Cannot connect to backend server at ${API_BASE_URL}. Please ensure the backend is running.`
    );
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      if (typeof errorJson.detail === "string") {
        errorDetail = errorJson.detail;
      } else if (Array.isArray(errorJson.detail)) {
        errorDetail = errorJson.detail
          .map((item: { msg?: string; loc?: string[] }) => item.msg || JSON.stringify(item))
          .join("; ");
      }
    } catch {
      // Body not JSON
    }

    if (response.status === 401) {
      // Clear token on authentication failure
      setStoredToken(null);
    }

    throw new ApiError(response.status, errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Authentication
  async register(data: {
    email: string;
    password: string;
    full_name?: string;
    phone_number?: string;
  }): Promise<User> {
    return request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async login(data: { email: string; password: string }): Promise<AuthToken> {
    const res = await request<AuthToken>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
    setStoredToken(res.access_token);
    return res;
  },

  async getMe(): Promise<User> {
    return request<User>("/auth/me", {
      method: "GET",
    });
  },

  logout(): void {
    setStoredToken(null);
  },

  // User Location
  async updateLocation(data: {
    latitude: number;
    longitude: number;
  }): Promise<UserLocationResponse> {
    return request<UserLocationResponse>("/users/me/location", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  // Emergency Reports
  async createReport(
    data: EmergencyReportCreate
  ): Promise<EmergencyReportSubmissionResponse> {
    if (data.photo) {
      const formData = new FormData();
      formData.append("emergency_type", data.emergency_type);
      formData.append("description", data.description);
      formData.append("severity", data.severity);
      formData.append("latitude", data.latitude.toString());
      formData.append("longitude", data.longitude.toString());
      formData.append("photo", data.photo);

      return request<EmergencyReportSubmissionResponse>("/reports", {
        method: "POST",
        body: formData,
      });
    }

    return request<EmergencyReportSubmissionResponse>("/reports", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getPhotoUrl(path?: string | null): string | null {
    if (!path) return null;
    if (path.startsWith("http://") || path.startsWith("https://")) return path;
    const base = API_BASE_URL.replace(/\/api\/v1\/?$/, "");
    return `${base}${path.startsWith("/") ? "" : "/"}${path}`;
  },

  async getReport(reportId: string): Promise<EmergencyReportResponse> {
    return request<EmergencyReportResponse>(`/reports/${encodeURIComponent(reportId)}`, {
      method: "GET",
    });
  },

  // Incidents
  async getIncidents(params?: {
    emergency_type?: string;
    severity?: string;
    latitude?: number;
    longitude?: number;
    radius_meters?: number;
  }): Promise<Incident[]> {
    const query = new URLSearchParams();
    if (params) {
      if (params.emergency_type) query.append("emergency_type", params.emergency_type);
      if (params.severity) query.append("severity", params.severity);
      if (params.latitude !== undefined) query.append("latitude", params.latitude.toString());
      if (params.longitude !== undefined) query.append("longitude", params.longitude.toString());
      if (params.radius_meters !== undefined) query.append("radius_meters", params.radius_meters.toString());
    }
    const qStr = query.toString() ? `?${query.toString()}` : "";
    return request<Incident[]>(`/incidents${qStr}`, {
      method: "GET",
    });
  },

  async getIncidentDetail(incidentId: string): Promise<IncidentDetail> {
    return request<IncidentDetail>(`/incidents/${encodeURIComponent(incidentId)}`, {
      method: "GET",
    });
  },

  async updateIncidentStatus(
    incidentId: string,
    status: IncidentStatus
  ): Promise<IncidentDetail> {
    return request<IncidentDetail>(`/incidents/${encodeURIComponent(incidentId)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },

  // Alerts
  async getAlerts(unreadOnly: boolean = false): Promise<Alert[]> {
    const qStr = unreadOnly ? "?unread_only=true" : "";
    return request<Alert[]>(`/alerts${qStr}`, {
      method: "GET",
    });
  },

  async markAlertRead(alertId: string): Promise<Alert> {
    return request<Alert>(`/alerts/${encodeURIComponent(alertId)}/read`, {
      method: "PATCH",
    });
  },
};
