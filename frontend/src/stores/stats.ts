// stats store — 今日看板数据（含 streak）
import { defineStore } from "pinia";
import { ref } from "vue";
import { statsApi, checkinsApi } from "@/api/checkins";
import type { TodayStats, Streak, CheckinCreateInput, Checkin } from "@/api/types";

export const useStatsStore = defineStore("stats", () => {
  const today = ref<TodayStats | null>(null);
  const streak = ref<Streak | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function loadToday(date?: string) {
    loading.value = true;
    error.value = null;
    try {
      today.value = await statsApi.today(date);
      // 顺便刷 streak
      streak.value = {
        streak: today.value.streak,
        today_active: today.value.today_active,
        last_active_date: today.value.last_active_date,
        total_active_days: 0,
      };
    } catch (e: any) {
      error.value = e?.message || "加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function refreshStreak() {
    streak.value = await checkinsApi.streak();
  }

  async function upsertCheckin(payload: CheckinCreateInput): Promise<Checkin> {
    const checkin = await checkinsApi.upsert(payload);
    if (today.value && today.value.date === payload.date) {
      today.value.checkin = checkin;
    }
    await refreshStreak();
    return checkin;
  }

  function clear() {
    today.value = null;
    streak.value = null;
    error.value = null;
  }

  return {
    today,
    streak,
    loading,
    error,
    loadToday,
    refreshStreak,
    upsertCheckin,
    clear,
  };
});
