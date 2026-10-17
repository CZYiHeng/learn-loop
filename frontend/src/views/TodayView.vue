<script setup lang="ts">
// TodayView — 今日看板（M1 一等公民）
// 一次拉 /stats/today 聚合接口拿全：任务+打卡+streak
// ★ 决策 5：完成任务自动打卡
// ★ 决策 6：streak 不归零（昨日有但今日没动 → 显示昨日数）
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useTaskStore } from "@/stores/task";
import { useStatsStore } from "@/stores/stats";
import TaskItem from "@/components/task/TaskItem.vue";
import StreakBadge from "@/components/checkin/StreakBadge.vue";

const router = useRouter();
const taskStore = useTaskStore();
const statsStore = useStatsStore();

const todayStr = computed(() => new Date().toISOString().slice(0, 10));

const todayStats = computed(() => statsStore.today);
const streak = computed(() => statsStore.streak);
const completionRate = computed(() => {
  const summary = todayStats.value?.task_summary;
  if (!summary || summary.total === 0) return 0;
  return summary.completion_rate;
});

const tasks = computed(() => todayStats.value?.tasks ?? []);

async function loadAll() {
  await statsStore.loadToday(todayStr.value);
  // 把今日任务也同步到 taskStore（用于乐观更新）
  if (todayStats.value) {
    taskStore.tasks = [...(todayStats.value.tasks as any)];
  }
}

async function handleToggle(taskId: number) {
  const task = taskStore.tasks.find((t) => t.id === taskId);
  if (!task) return;
  try {
    if (task.status === "done") {
      await taskStore.uncompleteTask(taskId);
    } else {
      await taskStore.completeTask(taskId);
    }
    // 完成操作后刷新 stats（自动打卡会让 streak 变化）
    await statsStore.loadToday(todayStr.value);
  } catch (e) {
    console.error("toggle failed", e);
  }
}

async function handleDelete(taskId: number) {
  if (!confirm("删除这个任务？")) return;
  try {
    await taskStore.deleteTask(taskId);
    await loadAll();
  } catch (e) {
    console.error("delete failed", e);
  }
}

async function handleCheckin() {
  // 用户主动打卡：弹出输入时长
  const minutesStr = prompt("今天学习了多少分钟？", "60");
  if (!minutesStr) return;
  const minutes = parseInt(minutesStr, 10);
  if (isNaN(minutes) || minutes < 0) {
    alert("请输入有效数字");
    return;
  }
  try {
    await statsStore.upsertCheckin({
      date: todayStr.value,
      duration_minutes: minutes,
    });
    await loadAll();
  } catch (e) {
    console.error("checkin failed", e);
  }
}

onMounted(loadAll);
</script>

<template>
  <div class="today-view">
    <!-- 顶部：日期 + streak -->
    <header class="today-header">
      <div class="date-block">
        <div class="weekday">
          {{ new Date().toLocaleDateString("zh-CN", { weekday: "long" }) }}
        </div>
        <div class="date">{{ todayStr }}</div>
      </div>
      <StreakBadge :streak="streak" />
    </header>

    <!-- 进度环 + 概览 -->
    <section class="progress-section" v-if="todayStats">
      <div class="progress-ring">
        <svg width="80" height="80" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="34" fill="none" stroke="#eee" stroke-width="6" />
          <circle
            cx="40" cy="40" r="34" fill="none" stroke="#534AB7" stroke-width="6"
            stroke-dasharray="213.6"
            :stroke-dashoffset="213.6 * (1 - completionRate)"
            stroke-linecap="round"
            transform="rotate(-90 40 40)"
            style="transition: stroke-dashoffset 0.3s"
          />
        </svg>
        <div class="progress-text">
          <div class="progress-percent">{{ Math.round(completionRate * 100) }}%</div>
          <div class="progress-label">完成</div>
        </div>
      </div>
      <div class="summary">
        <div>今日 {{ todayStats.task_summary.total }} 个任务</div>
        <div>已完成 {{ todayStats.task_summary.completed }} 个</div>
        <div v-if="todayStats.task_summary.estimated_minutes_total > 0">
          预计 {{ todayStats.task_summary.estimated_minutes_total }} 分钟
        </div>
      </div>
    </section>

    <!-- 打卡按钮 -->
    <section class="checkin-section">
      <div v-if="todayStats?.checkin" class="checkin-done">
        ✅ 今日已打卡（{{ todayStats.checkin.source === "auto" ? "完成任务自动" : "手动" }}）
        <span v-if="todayStats.checkin.duration_minutes">
          · {{ todayStats.checkin.duration_minutes }} 分钟
        </span>
        <button class="link-btn" @click="handleCheckin">修改</button>
      </div>
      <button v-else class="checkin-btn touchable" @click="handleCheckin">
        💪 今日打卡
      </button>
    </section>

    <!-- 任务列表 -->
    <section class="tasks-section">
      <h2 class="section-title">今日任务</h2>
      <div v-if="tasks.length === 0 && !statsStore.loading" class="empty">
        <p>今天没有安排任务。</p>
        <button class="primary-btn" @click="router.push('/plans/new')">去新建计划</button>
      </div>
      <div v-else class="tasks-list">
        <TaskItem
          v-for="task in tasks"
          :key="task.id"
          :task="task"
          @toggle="handleToggle"
          @delete="handleDelete"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.today-view {
  padding: 16px;
  max-width: 720px;
  margin: 0 auto;
}

.today-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.weekday {
  font-size: 13px;
  color: #888;
}
.date {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a1a;
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  background: #fff;
  border-radius: var(--radius-md);
  margin-bottom: 16px;
  border: 1px solid #eee;
}
.progress-ring {
  position: relative;
  width: 80px;
  height: 80px;
}
.progress-text {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}
.progress-percent {
  font-size: 18px;
  font-weight: 600;
  color: #534AB7;
}
.progress-label {
  font-size: 10px;
  color: #888;
}
.summary {
  font-size: 13px;
  color: #555;
  line-height: 1.7;
}

.checkin-section {
  margin-bottom: 20px;
}
.checkin-btn {
  width: 100%;
  padding: 14px;
  background: #534AB7;
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
}
.checkin-done {
  padding: 12px 16px;
  background: #e1f5ee;
  color: #085041;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.link-btn {
  background: none;
  border: none;
  color: #534AB7;
  cursor: pointer;
  text-decoration: underline;
  font-size: 13px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 12px;
  color: #1a1a1a;
}
.empty {
  text-align: center;
  padding: 32px 16px;
  color: #888;
}
.primary-btn {
  margin-top: 12px;
  padding: 10px 20px;
  background: #534AB7;
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
