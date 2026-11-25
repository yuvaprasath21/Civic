import { apiClient } from "@/api/client";

export interface CitizenProfile {
  id: string;
  full_name: string;
  email: string;
  phone_number?: string;
  profile_image_url?: string;
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
  address_line?: string;
  city?: string;
  state?: string;
  pincode?: string;
  default_latitude?: number;
  default_longitude?: number;
  total_reports_submitted: number;
  reputation_score: number;
}

export interface UpdateCitizenProfilePayload {
  full_name?: string;
  phone_number?: string;
  address_line?: string;
  city?: string;
  state?: string;
  pincode?: string;
  default_latitude?: number;
  default_longitude?: number;
}

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api").replace(/\/api\/?$/, "");

export function resolveUploadUrl(path?: string): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("http")) return path;
  return `${API_ORIGIN}${path}`;
}

export const profileService = {
  async getMyProfile(): Promise<CitizenProfile> {
    const { data } = await apiClient.get<CitizenProfile>("/citizens/me");
    return data;
  },
  async updateMyProfile(payload: UpdateCitizenProfilePayload): Promise<CitizenProfile> {
    const { data } = await apiClient.put<CitizenProfile>("/citizens/me", payload);
    return data;
  },
  async uploadProfileImage(file: File): Promise<{ profile_image_url: string }> {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await apiClient.post<{ profile_image_url: string }>("/citizens/me/profile-image", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
};
