import { apiClient } from "@/api/client";
import type { IssueStatus, PriorityLevel } from "@/types/domain";
import type { IssueComment, IssueDetail, IssueImage, IssueSummary } from "@/services/issueService";

export type AssignmentStatus = "PENDING" | "ACCEPTED" | "IN_PROGRESS" | "COMPLETED" | "REASSIGNED";

export interface StaffIssueSummary extends IssueSummary {
  assignment_status: AssignmentStatus;
  progress_percent: number;
  assigned_at: string;
}

export interface PaginatedStaffIssues {
  items: StaffIssueSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface StaffIssueDetail extends IssueDetail {
  assignment_status: AssignmentStatus;
  accepted_at?: string;
  started_at?: string;
  completed_at?: string;
  staff_notes?: string;
}

export interface StaffStats {
  employee_code?: string;
  designation?: string;
  department_name?: string;
  current_workload: number;
  total_resolved: number;
  average_resolution_hours?: number;
  pending: number;
  accepted: number;
  in_progress: number;
}

export interface ActionResult {
  message: string;
  assignment_status: AssignmentStatus;
  issue_status: IssueStatus;
  progress_percent: number;
}

export const staffService = {
  async stats(): Promise<StaffStats> {
    return (await apiClient.get<StaffStats>("/staff/me")).data;
  },
  async listIssues(params: { priority?: PriorityLevel; status?: IssueStatus; page?: number; page_size?: number } = {}) {
    return (await apiClient.get<PaginatedStaffIssues>("/staff/issues", { params })).data;
  },
  async history(params: { page?: number; page_size?: number } = {}) {
    return (await apiClient.get<PaginatedStaffIssues>("/staff/history", { params })).data;
  },
  async getIssue(id: string) {
    return (await apiClient.get<StaffIssueDetail>(`/staff/issues/${id}`)).data;
  },
  async accept(id: string) {
    return (await apiClient.put<ActionResult>(`/staff/issues/${id}/accept`)).data;
  },
  async start(id: string) {
    return (await apiClient.put<ActionResult>(`/staff/issues/${id}/start`)).data;
  },
  async addNote(id: string, body: string, visible_to_citizen: boolean) {
    return (await apiClient.post<IssueComment>(`/staff/issues/${id}/notes`, { body, visible_to_citizen })).data;
  },
  async updateProgress(id: string, percent: number, note?: string) {
    return (await apiClient.put<ActionResult>(`/staff/issues/${id}/progress`, { percent, note })).data;
  },
  async uploadPhotos(id: string, image_type: "BEFORE_WORK" | "AFTER_WORK", files: File[]) {
    const form = new FormData();
    form.append("image_type", image_type);
    files.forEach((f) => form.append("images", f));
    return (
      await apiClient.post<{ images: IssueImage[] }>(`/staff/issues/${id}/photos`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
    ).data;
  },
  async resolve(id: string, notes?: string) {
    return (await apiClient.put<ActionResult>(`/staff/issues/${id}/resolve`, { notes })).data;
  },
};
