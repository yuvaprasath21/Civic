import { apiClient } from "@/api/client";

export interface OtpSentResponse {
  message: string;
  email_sent: boolean;
  mobile_sent: boolean;
  expires_in_seconds: number;
}

export const otpService = {
  async send(payload: { email?: string; mobile?: string }): Promise<OtpSentResponse> {
    const { data } = await apiClient.post<OtpSentResponse>("/auth/send-otp", payload);
    return data;
  },
  async resend(payload: { email?: string; mobile?: string }): Promise<OtpSentResponse> {
    const { data } = await apiClient.post<OtpSentResponse>("/auth/resend-otp", payload);
    return data;
  },
  async verifyEmail(email: string, otp: string): Promise<void> {
    await apiClient.post("/auth/verify-email-otp", { email, otp });
  },
  async verifyMobile(mobile: string, otp: string): Promise<void> {
    await apiClient.post("/auth/verify-mobile-otp", { mobile, otp });
  },
};
