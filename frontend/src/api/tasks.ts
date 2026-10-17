// tasks API 封装
import { api } from "./client";
import type { Task, TaskCreateInput, TaskRescheduleInput } from "./types";

export const tasksApi = {
  list: (params: { plan_id?: number; planned_date?: string; status?: string }) =>
    api.get<Task[]>("/tasks" + "?" + new URLSearchParams(params as any).toString()),

  get: (id: number) => api.get<Task>(`/tasks/${id}`),

  create: (payload: TaskCreateInput) => api.post<Task>("/tasks", payload),

  update: (id: number, payload: Partial<TaskCreateInput> & { status?: string; actual_minutes?: number }) =>
    api.patch<Task>(`/tasks/${id}`, payload),

  complete: (id: number, actual_minutes?: number) =>
    api.post<Task>(`/tasks/${id}/complete`, actual_minutes ? { actual_minutes } : {}),

  uncomplete: (id: number) => api.post<Task>(`/tasks/${id}/uncomplete`, {}),

  reschedule: (id: number, new_date: string) =>
    api.post<Task>(`/tasks/${id}/reschedule`, { new_date } as TaskRescheduleInput),

  batch: (payload: { task_ids: number[]; stage_title?: string; status?: string }) =>
    api.post<{ updated: number; failed: number[] }>("/tasks:batch", payload),

  delete: (id: number) => api.delete<void>(`/tasks/${id}`),
};
