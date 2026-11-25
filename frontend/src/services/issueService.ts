import { apiClient } from "@/api/client";
import type { IssueCategory, IssueStatus, SeverityLevel, PriorityLevel } from "@/types/domain";

export interface LocationData {
  latitude: number;
  longitude: number;
  address_text?: string;
  landmark?: string;
  ward?: string;
  city?: string;
  pincode?: string;
}

export interface IssueImage {
  id: number;
  image_type: string;
  url: string;
  width?: number;
  height?: number;
  created_at: string;
}

export interface StatusHistoryEntry {
  from_status: IssueStatus | null;
  to_status: IssueStatus;
  note?: string;
  changed_by_name?: string;
  created_at: string;
}

export interface IssueComment {
  id: number;
  author_name: string;
  author_role: string;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface IssueFeedback {
  rating: number;
  comment?: string;
  created_at: string;
}

export interface AIPredictionSummary {
  category: IssueCategory;
  confidence: number;
  severity: SeverityLevel;
  detected_objects: string[];
  model_version: string;
  provider: string;
}

export interface IssueSummary {
  id: string;
  reference_code: string;
  title: string;
  category: IssueCategory;
  severity: SeverityLevel;
  status: IssueStatus;
  priority_level: PriorityLevel;
  priority_score: number;
  location: LocationData;
  thumbnail_url?: string;
  created_at: string;
  department_name?: string;
}

export interface IssueDetail {
  id: string;
  reference_code: string;
  title: string;
  description?: string;
  category: IssueCategory;
  severity: SeverityLevel;
  status: IssueStatus;
  priority_level: PriorityLevel;
  priority_score: number;
  is_ai_verified: boolean;
  is_citizen_edited_category: boolean;
  location: LocationData;
  department_name?: string;
  reporter_name: string;
  reporter_id: string;
  images: IssueImage[];
  video_url?: string;
  ai_prediction?: AIPredictionSummary;
  status_history: StatusHistoryEntry[];
  comments: IssueComment[];
  feedback?: IssueFeedback;
  assigned_to_name?: string;
  progress_percent?: number;
  duplicate_count: number;
  report_count: number;
  master_issue_id?: string;
  master_reference_code?: string;
  created_at: string;
  resolved_at?: string;
}

export interface PaginatedIssues {
  items: IssueSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateIssuePayload {
  title: string;
  description?: string;
  category: IssueCategory;
  severity: SeverityLevel;
  latitude: number;
  longitude: number;
  address_text?: string;
  landmark?: string;
  ward?: string;
  city?: string;
  pincode?: string;
  images: File[];
  video?: File;
}

export interface IssueListFilters {
  category?: IssueCategory;
  status?: IssueStatus;
  severity?: SeverityLevel;
  city?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const issueService = {
  async createIssue(payload: CreateIssuePayload): Promise<IssueDetail> {
    const form = new FormData();
    form.append("title", payload.title);
    if (payload.description) form.append("description", payload.description);
    form.append("category", payload.category);
    form.append("severity", payload.severity);
    form.append("latitude", String(payload.latitude));
    form.append("longitude", String(payload.longitude));
    if (payload.address_text) form.append("address_text", payload.address_text);
    if (payload.landmark) form.append("landmark", payload.landmark);
    if (payload.ward) form.append("ward", payload.ward);
    if (payload.city) form.append("city", payload.city);
    if (payload.pincode) form.append("pincode", payload.pincode);
    payload.images.forEach((file) => form.append("images", file));
    if (payload.video) form.append("video", payload.video);

    const { data } = await apiClient.post<IssueDetail>("/issues", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
  async listIssues(filters: IssueListFilters = {}): Promise<PaginatedIssues> {
    const { data } = await apiClient.get<PaginatedIssues>("/issues", { params: filters });
    return data;
  },
  async listMyIssues(filters: IssueListFilters = {}): Promise<PaginatedIssues> {
    const { data } = await apiClient.get<PaginatedIssues>("/my/issues", { params: filters });
    return data;
  },
  async listNearby(latitude: number, longitude: number, radius_km = 3): Promise<PaginatedIssues> {
    const { data } = await apiClient.get<PaginatedIssues>("/issues/nearby", {
      params: { latitude, longitude, radius_km },
    });
    return data;
  },
  async getIssue(id: string): Promise<IssueDetail> {
    const { data } = await apiClient.get<IssueDetail>(`/issues/${id}`);
    return data;
  },
  async updateIssue(
    id: string,
    payload: Partial<Pick<CreateIssuePayload, "title" | "description" | "category" | "severity">>
  ): Promise<IssueDetail> {
    const { data } = await apiClient.put<IssueDetail>(`/issues/${id}`, payload);
    return data;
  },
  async addComment(id: string, body: string): Promise<IssueComment> {
    const { data } = await apiClient.post<IssueComment>(`/issues/${id}/comments`, { body });
    return data;
  },
  async addFeedback(id: string, rating: number, comment?: string): Promise<IssueFeedback> {
    const { data } = await apiClient.post<IssueFeedback>(`/issues/${id}/feedback`, { rating, comment });
    return data;
  },
};
