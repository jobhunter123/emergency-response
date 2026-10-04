/**
 * Shared API domain models and schema definitions.
 * Matches backend FastAPI schemas strictly.
 */

export type EmergencyType =
  | "FIRE"
  | "FLOOD"
  | "ACCIDENT"
  | "MEDICAL"
  | "EARTHQUAKE"
  | "STORM"
  | "LANDSLIDE"
  | "MISSING_PERSON"
  | "UNSAFE_SITUATION"
  | "OTHER";

export type SeverityLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type IncidentStatus =
  | "UNVERIFIED"
  | "VERIFYING"
  | "CONFIRMED"
  | "RESPONDING"
  | "CONTAINED"
  | "RESOLVED"
  | "FALSE_ALARM";

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface BoundingBox {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface AffectedArea {
  center: Coordinates;
  radius_meters: number;
  bounds?: BoundingBox | null;
}

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  phone_number?: string | null;
  is_active: boolean;
  is_responder: boolean;
  latitude?: number | null;
  longitude?: number | null;
  location_updated_at?: string | null;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface UserLocationResponse {
  latitude: number;
  longitude: number;
  location_updated_at?: string | null;
}

export interface Incident {
  id: string;
  emergency_type: EmergencyType;
  title: string;
  description?: string | null;
  severity: SeverityLevel;
  status: IncidentStatus;
  latitude: number;
  longitude: number;
  affected_radius_meters: number;
  confidence_score: number;
  corroboration_count: number;
  created_at: string;
  updated_at: string;
  confirmed_at?: string | null;
}

export interface IncidentDetail extends Incident {
  report_count: number;
  confidence_level?: string | null;
  affected_area?: AffectedArea | null;
  affected_user_count: number;
  evidence_photos?: string[];
}

export interface EmergencyReportCreate {
  emergency_type: EmergencyType;
  description: string;
  severity: SeverityLevel;
  latitude: number;
  longitude: number;
  photo?: File | null;
}

export interface EmergencyReportResponse {
  id: string;
  incident_id?: string | null;
  user_id: string;
  emergency_type: EmergencyType;
  description: string;
  severity: SeverityLevel;
  latitude: number;
  longitude: number;
  reported_at: string;
  confidence_contribution: number;
  is_independent: boolean;
  photo_url?: string | null;
}

export interface IncidentSummary {
  id: string;
  status: IncidentStatus;
  confidence_score: number;
  corroboration_count: number;
  confidence_level?: string | null;
}

export interface EmergencyReportSubmissionResponse {
  report: EmergencyReportResponse;
  incident: IncidentSummary;
}

export interface Alert {
  id: string;
  incident_id: string;
  title: string;
  message: string;
  severity: SeverityLevel;
  created_at: string;
  read_at?: string | null;
  is_read: boolean;
}
