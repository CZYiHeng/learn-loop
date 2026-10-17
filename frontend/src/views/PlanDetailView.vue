<script setup lang="ts">
// PlanDetailView — 计划详情（阶段聚合 + 任务列表）
// ★ 决策 2：阶段不单独建表，由 service 层 GROUP BY
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { usePlanStore } from "@/stores/plan";
import { useTaskStore } from "@/stores/task";
import { tasksApi } from "@/api/tasks";
import type { Task } from "@/api/types";

const route = useRoute();
const router = useRouter();
const planStore = usePlanStore();
const taskStore = useTaskStore();

const planId = computed(() => Number(route.params.id));
const plan = computed(() => planStore.currentPlan);
const progress = computed(() => planStore.currentProgress);

// 完整任务列表（不只是今日）
const allTasks = ref<Task[]>([]);

async function loadAll() {
  await planStore.loadDetail(planId.value);
  allTasks.value = await tasksApi.list({ plan_id: planId.value });
}

function stages() {
  // 客户端阶段聚合（决策 2）
  const groups: Record<string, Task[]> = {};
  for (const t of allTasks.value) {
    const stage = t.stage_title || "未分组";
    groups[stage] = groups[stage] || [];
    groups[stage].push(t);
  }
  return Object.entries(groups).map(([stage, tasks]) => ({
    stage,
    tasks: tasks.sort((a, b) => a.planned_date.localeCompare(b.planned_date)),
  }));
}

async function handleToggle(taskId: number) {
  const task = allTasks.value.find((t) => t.id === taskId);
  if (!task) return;
  if (task.status === "done") {
    await taskStore.uncompleteTask(taskId);
    // 这里不直接调 taskStore，因为 taskStore.tasks 是今日视图的
    const updated = await tasksApi.uncomplete(taskId);
    const idx = allTasks.value.findIndex((t) => t.id === taskId);
    if (idx >= 0) allTasks.value[idx] = updated;
  } else {
    const updated = await tasksApi.complete(taskId);
    const idx = allTasks.value.findIndex((t) => t.id === taskId);
    if (idx >= 0) allTasks.value[idx] = updated;
  }
  await planStore.loadDetail(planId.value);
}

async function handleDelete(taskId: number) {
  if (!confirm("删除？")) return;
  await tasksApi.delete(taskId);
  allTasks.value = allTasks.value.filter((t) => t.id !== taskId);
  await planStore.loadDetail(planId.value);
}

onMounted(loadAll);
</script>

<template>
  <div class="plan-detail-view">
    <header class="view-header">
      <button class="ghost-btn" @click="router.back()">←</button>
      <h1 v-if="plan">{{ plan.title }}</h1>
      <h1 v-else>计划详情</h1>
    </header>

    <div v-if="planStore.loading" class="loading">加载中…</div>

    <section v-if="progress" class="progress-section">
      <h2>整体进度</h2>
      <div class="progress-bar-bg">
        <div
          class="progress-bar-fill"
          :style="{ width: `${progress.completion_rate * 100}%` }"
        ></div>
      </div>
      <div class="progress-stats">
        <span>完成 {{ progress.completed_tasks }} / {{ progress.total_tasks }}</span>
        <span>跳过 {{ progress.skipped_tasks }}</span>
        <span>准时率 {{ Math.round(progress.on_time_rate * 100) }}%</span>
      </div>
    </section>

    <section v-if="plan" class="info-section">
      <div class="info-row">
        <span>场景</span>
        <span>{{ { student: "学生", worker: "在职", kaoyan: "考研", cert: "考证" }[plan.scenario] }}</span>
      </div>
      <div class="info-row">
        <span>周期</span>
        <span>{{ plan.start_date }} → {{ plan.end_date }}（{{ plan.weeks }} 周，每周 {{ plan.weekly_hours }}h）</span>
      </div>
    </section>

    <!-- ★ 决策 2：阶段聚合 -->
    <section v-for="group in stages()" :key="group.stage" class="stage-section">
      <h3 class="stage-title">{{ group.stage }}</h3>
      <div class="stage-tasks">
        <div
          v-for="task in group.tasks"
          :key="task.id"
          class="task-row"
          :class="{ done: task.status === 'done' }"
        >
          <button
            class="checkbox touchable"
            :class="{ checked: task.status === 'done' }"
            @click="handleToggle(task.id)"
            type="button"
          >
            <span v-if="task.status === 'done'">✓</span>
          </button>
          <div class="task-info">
            <div class="task-title">{{ task.title }}</div>
            <div class="task-meta">
              <span>{{ task.planned_date }}</span>
              <span>{{ task.estimated_minutes }} 分钟</span>
              <span v-if="task.shift_count > 0">改期 ×{{ task.shift_count }}</span>
            </div>
          </div>
          <button class="remove-btn" @click="handleDelete(task.id)" type="button">×</button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.plan-detail-view {
  padding: 16px;
  max-width: 720px;
  margin: 0 auto;
}
.view-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.view-header h1 {
  font-size: 22px;
  margin: 0;
  flex: 1;
}
.ghost-btn {
  background: none;
  border: 1px solid #ddd;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
}
.loading {
  text-align: center;
  padding: 24px;
  color: #888;
}
.progress-section, .info-section {
  background: #fff;
  border: 1px solid #eee;
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 16px;
}
.progress-section h2, .stage-title {
  font-size: 14px;
  color: #534AB7;
  margin: 0 0 10px;
}
.progress-bar-bg {
  width: 100%;
  height: 8px;
  background: #eee;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
}
.progress-bar-fill {
  height: 100%;
  background: #534AB7;
  transition: width 0.3s;
}
.progress-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #888;
}
.info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px solid #f5f5f5;
}
.info-row:last-child {
  border-bottom: none;
}
.info-row span:first-child {
  color: #888;
}
.stage-section {
  margin-bottom: 20px;
}
.stage-tasks {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.task-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: var(--radius-sm);
}
.task-row.done {
  opacity: 0.55;
}
.task-row.done .task-title {
  text-decoration: line-through;
}
.checkbox {
  width: 24px;
  height: 24px;
  border: 2px solid #534AB7;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  padding: 0;
  margin-top: 1px;
}
.checkbox.checked {
  background: #534AB7;
}
.task-info {
  flex: 1;
  min-width: 0;
}
.task-title {
  font-size: 14px;
  margin-bottom: 4px;
}
.task-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: #888;
}
.remove-btn {
  background: none;
  border: none;
  color: #ccc;
  cursor: pointer;
  font-size: 18px;
  padding: 0;
}
.remove-btn:hover {
  color: #c00;
}
</style>
