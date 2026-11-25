export type UserRole = "CITIZEN" | "FIELD_STAFF" | "DEPARTMENT_ADMIN" | "SUPER_ADMIN";

export type IssueCategory =
  | "POTHOLE" | "GARBAGE" | "BROKEN_STREETLIGHT" | "WATER_LEAKAGE" | "DRAINAGE"
  | "WATERLOGGING" | "FALLEN_TREE" | "DAMAGED_SIGN" | "ILLEGAL_DUMPING"
  | "CONSTRUCTION_OBSTRUCTION" | "OTHER";

export type SeverityLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type PriorityLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type IssueStatus =
  | "REPORTED" | "AI_ANALYZED" | "VERIFIED" | "ASSIGNED" | "ACCEPTED"
  | "IN_PROGRESS" | "RESOLVED" | "REJECTED" | "REOPENED" | "CLOSED" | "POTENTIAL_DUPLICATE";

export interface AIAnalysisResult {
  category: IssueCategory;
  confidence: number;
  severity: SeverityLevel;
  detected_objects: string[];
  model_version: string;
}

export interface GeoLocation {
  latitude: number;
  longitude: number;
  address_text?: string;
  landmark?: string;
  ward?: string;
  city?: string;
}

export interface CivicIssueSummary {
  id: string;
  reference_code: string;
  title: string;
  category: IssueCategory;
  severity: SeverityLevel;
  status: IssueStatus;
  priority_level: PriorityLevel;
  priority_score: number;
  location: GeoLocation;
  created_at: string;
  department_name?: string;
}

export interface User {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  profile_image_url?: string;
}

export interface ApiErrorShape {
  success: false;
  message: string;
  error_code: string;
}
