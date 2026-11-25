import type { IssueCategory, IssueStatus, SeverityLevel, PriorityLevel } from "@/types/domain";

export const CATEGORY_LABELS: Record<IssueCategory, string> = {
  POTHOLE: "Pothole",
  GARBAGE: "Garbage Accumulation",
  BROKEN_STREETLIGHT: "Broken Streetlight",
  WATER_LEAKAGE: "Water Leakage",
  DRAINAGE: "Drainage Problem",
  WATERLOGGING: "Waterlogging",
  FALLEN_TREE: "Fallen Tree",
  DAMAGED_SIGN: "Damaged Road Sign",
  ILLEGAL_DUMPING: "Illegal Dumping",
  CONSTRUCTION_OBSTRUCTION: "Construction Obstruction",
  OTHER: "Other Civic Issue",
};

export const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({
  value: value as IssueCategory,
  label,
}));

export const SEVERITY_LABELS: Record<SeverityLevel, string> = {
  LOW: "Low", MEDIUM: "Medium", HIGH: "High", CRITICAL: "Critical",
};

export const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  LOW: "text-severity-low bg-severity-low/10",
  MEDIUM: "text-severity-medium bg-severity-medium/10",
  HIGH: "text-severity-high bg-severity-high/10",
  CRITICAL: "text-severity-critical bg-severity-critical/10",
};

export const PRIORITY_COLORS: Record<PriorityLevel, string> = {
  LOW: "text-severity-low bg-severity-low/10",
  MEDIUM: "text-severity-medium bg-severity-medium/10",
  HIGH: "text-severity-high bg-severity-high/10",
  CRITICAL: "text-severity-critical bg-severity-critical/10",
};

export const STATUS_LABELS: Record<IssueStatus, string> = {
  REPORTED: "Reported", AI_ANALYZED: "AI Analyzed", VERIFIED: "Verified", ASSIGNED: "Assigned",
  ACCEPTED: "Accepted", IN_PROGRESS: "In Progress", RESOLVED: "Resolved", REJECTED: "Rejected",
  REOPENED: "Reopened", CLOSED: "Closed", POTENTIAL_DUPLICATE: "Potential Duplicate",
};

export const STATUS_COLORS: Record<IssueStatus, string> = {
  REPORTED: "text-slate-600 bg-slate-100",
  AI_ANALYZED: "text-brand-700 bg-brand-50",
  VERIFIED: "text-brand-700 bg-brand-100",
  ASSIGNED: "text-amber-700 bg-amber-50",
  ACCEPTED: "text-amber-700 bg-amber-100",
  IN_PROGRESS: "text-amber-800 bg-amber-100",
  RESOLVED: "text-emerald-700 bg-emerald-50",
  REJECTED: "text-red-700 bg-red-50",
  REOPENED: "text-orange-700 bg-orange-50",
  CLOSED: "text-slate-500 bg-slate-100",
  POTENTIAL_DUPLICATE: "text-purple-700 bg-purple-50",
};
