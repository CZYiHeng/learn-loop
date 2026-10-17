// plan store — 计划列表 + 当前计划
import { defineStore } from "pinia";
import { ref } from "vue";
import { plansApi } from "@/api/plans";
import type { StudyPlan, PlanProgress, PlanCreateInput } from "@/api/types";

export const usePlanStore = defineStore("plan", () => {
  const plans = ref<StudyPlan[]>([]);
  const currentPlan = ref<StudyPlan | null>(null);
  const currentProgress = ref<PlanProgress | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function load() {
    loading.value = true;
    try {
      const result = await plansApi.list();
      plans.value = result.items;
    } catch (e: any) {
      error.value = e?.message || "加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function loadDetail(id: number) {
    loading.value = true;
    try {
      currentPlan.value = await plansApi.get(id);
      currentProgress.value = await plansApi.progress(id);
    } catch (e: any) {
      error.value = e?.message || "加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function create(payload: PlanCreateInput) {
    const plan = await plansApi.create(payload);
    plans.value.unshift(plan);
    return plan;
  }

  function clear() {
    plans.value = [];
    currentPlan.value = null;
    currentProgress.value = null;
  }

  return {
    plans,
    currentPlan,
    currentProgress,
    loading,
    error,
    load,
    loadDetail,
    create,
    clear,
  };
});
