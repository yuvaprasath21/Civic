import { apiClient } from "@/api/client";
import type { IssueCategory, SeverityLevel } from "@/types/domain";

export interface AIAnalysisPreview {
  category: IssueCategory;
  confidence: number;
  severity: SeverityLevel;
  detected_objects: string[];
  model_version: string;
}

export const aiService = {
  async analyzeImage(file: File): Promise<AIAnalysisPreview> {
    const form = new FormData();
    form.append("image", file);
    const { data } = await apiClient.post<AIAnalysisPreview>("/ai/analyze-image", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
};
