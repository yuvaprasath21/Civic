import axios, { AxiosError } from "axios";
import type { ApiErrorShape } from "@/types/domain";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("civic_access_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export class ApiError extends Error {
  errorCode: string;
  status?: number;

  constructor(message: string, errorCode: string, status?: number) {
    super(message);
    this.errorCode = errorCode;
    this.status = status;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorShape>) => {
    const data = error.response?.data;
    const message = data?.message ?? "Something went wrong. Please try again.";
    const errorCode = data?.error_code ?? "UNKNOWN_ERROR";
    return Promise.reject(new ApiError(message, errorCode, error.response?.status));
  }
);
