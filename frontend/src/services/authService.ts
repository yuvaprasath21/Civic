import { apiClient } from "@/api/client";
import type { User } from "@/types/domain";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  phone_number?: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export const authService = {
  async register(payload: RegisterPayload): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>("/auth/register", payload);
    return data;
  },
  async login(payload: LoginPayload): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
    return data;
  },
  async me(): Promise<User> {
    const { data } = await apiClient.get<User>("/auth/me");
    return data;
  },
  async forgotPassword(email: string): Promise<{ message: string; dev_reset_token?: string }> {
    const { data } = await apiClient.post("/auth/forgot-password", { email });
    return data;
  },
  async resetPassword(token: string, new_password: string): Promise<{ message: string }> {
    const { data } = await apiClient.post("/auth/reset-password", { token, new_password });
    return data;
  },
  async refresh(refresh_token: string): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>("/auth/refresh", { refresh_token });
    return data;
  },
};
