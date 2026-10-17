// checkins + stats API 封装
import { api } from "./client";
import type { Checkin, Streak, TodayStats, CheckinCreateInput } from "./types";

export const checkinsApi = {
  list: (start: string, end: string) =>
    api.get<Checkin[]>(`/checkins?start=${start}&end=${end}`),

  streak: () => api.get<Streak>("/checkins/streak"),

  upsert: (payload: CheckinCreateInput) => api.post<Checkin>("/checkins", payload),

  update: (date: string, payload: Partial<CheckinCreateInput>) =>
    api.patch<Checkin>(`/checkins/${date}`, payload),

  delete: (date: string) => api.delete<void>(`/checkins/${date}`),
};

export const statsApi = {
  today: (today?: string) =>
    api.get<TodayStats>("/stats/today" + (today ? `?today=${today}` : "")),
};
