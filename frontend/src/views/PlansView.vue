<script setup lang="ts">
// PlansView — 计划列表
import { onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { usePlanStore } from "@/stores/plan";

const router = useRouter();
const planStore = usePlanStore();

const plans = computed(() => planStore.plans);

function statusLabel(s: string): string {
  return { active: "进行中", draft: "草稿", archived: "已归档", abandoned: "已弃用" }[s] || s;
}

function statusColor(s: string): string {
  return { active: "#085041", draft: "#ba7517", archived: "#888", abandoned: "#c00" }[s] || "#888";
}

onMounted(() => planStore.load());
</script>

<template>
  <div class="plans-view">
    <header class="view-header">
      <h1>学习计划</h1>
      <button class="primary-btn" @click="router.push('/plans/new')">+ 新建</button>
    </header>

    <div v-if="planStore.loading" class="loading">加载中…</div>
    <div v-else-if="plans.length === 0" class="empty">
      <p>还没有学习计划。</p>
      <button class="primary-btn" @click="router.push('/plans/new')">创建第一个</button>
    </div>
    <div v-else class="plans-list">
      <div
        v-for="plan in plans"
        :key="plan.id"
        class="plan-card"
        @click="router.push(`/plans/${plan.id}`)"
      >
        <div class="plan-title">{{ plan.title }}</div>
        <div class="plan-meta">
          <span class="plan-scenario">{{ { student: "学生", worker: "在职", kaoyan: "考研", cert: "考证" }[plan.scenario] || plan.scenario }}</span>
          <span class="plan-period">{{ plan.start_date }} → {{ plan.end_date }}</span>
          <span class="plan-status" :style="{ color: statusColor(plan.status) }">
            {{ statusLabel(plan.status) }}
          </span>
        </div>
        <div class="plan-origin" v-if="plan.origin === 'ai'">✨ AI 生成</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plans-view {
  padding: 16px;
  max-width: 720px;
  margin: 0 auto;
}
.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.view-header h1 {
  font-size: 22px;
  margin: 0;
}
.primary-btn {
  padding: 8px 14px;
  background: #534AB7;
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
}
.loading, .empty {
  text-align: center;
  padding: 32px 16px;
  color: #888;
}
.plans-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.plan-card {
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color 0.15s;
}
.plan-card:hover {
  border-color: #534AB7;
}
.plan-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 6px;
  color: #1a1a1a;
}
.plan-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: #888;
}
.plan-status {
  font-weight: 500;
}
.plan-origin {
  margin-top: 6px;
  font-size: 11px;
  color: #534AB7;
}
</style>
