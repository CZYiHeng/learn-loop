// plans API 封装
import { api } from "./client";
import type { PageResponse, StudyPlan, PlanProgress, PlanCreateInput } from "./types";

export const plansApi = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    api.get<PageResponse<StudyPlan>>("/plans" + (params ? "?" + new URLSearchParams(params as any).toString() : "")),

  get: (id: number) => api.get<StudyPlan>(`/plans/${id}`),

  create: (payload: PlanCreateInput) => api.post<StudyPlan>("/plans", payload),

  update: (id: number, payload: Partial<PlanCreateInput> & { status?: string }) =>
    api.patch<StudyPlan>(`/plans/${id}`, payload),

  delete: (id: number) => api.delete<void>(`/plans/${id}`),

  progress: (id: number) => api.get<PlanProgress>(`/plans/${id}/progress`),
};
