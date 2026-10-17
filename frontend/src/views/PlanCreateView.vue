<script setup lang="ts">
// PlanCreateView — 手工新建计划（M3 会被首页 FirstPlanPrompt 替代）
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { usePlanStore } from "@/stores/plan";
import { useTaskStore } from "@/stores/task";

const router = useRouter();
const planStore = usePlanStore();
const taskStore = useTaskStore();

// 计划基本信息
const title = ref("");
const goal = ref("");
const scenario = ref<"student" | "worker" | "kaoyan" | "cert">("worker");
const weeks = ref(4);
const weeklyHours = ref(8);
const startDate = ref(new Date().toISOString().slice(0, 10));
const endDate = computed(() => {
  const d = new Date(startDate.value);
  d.setDate(d.getDate() + weeks.value * 7);
  return d.toISOString().slice(0, 10);
});

// 任务列表（手工添加）
interface DraftTask {
  title: string;
  planned_date: string;
  estimated_minutes: number;
  stage_title: string;
}
const draftTasks = ref<DraftTask[]>([{ title: "", planned_date: startDate.value, estimated_minutes: 60, stage_title: "" }]);
const error = ref<string>("");

function addTask() {
  draftTasks.value.push({
    title: "",
    planned_date: startDate.value,
    estimated_minutes: 60,
    stage_title: "",
  });
}

function removeTask(idx: number) {
  draftTasks.value.splice(idx, 1);
}

async function submit() {
  error.value = "";
  if (!title.value.trim()) {
    error.value = "标题不能为空";
    return;
  }
  if (draftTasks.value.length === 0) {
    error.value = "至少添加一个任务";
    return;
  }
  if (draftTasks.value.some((t) => !t.title.trim())) {
    error.value = "有任务标题为空";
    return;
  }

  try {
    const plan = await planStore.create({
      title: title.value,
      goal: goal.value || undefined,
      scenario: scenario.value,
      origin: "manual",
      weeks: weeks.value,
      weekly_hours: weeklyHours.value,
      start_date: startDate.value,
      end_date: endDate.value,
    });

    // 创建任务
    for (const t of draftTasks.value) {
      await taskStore.createTask({
        plan_id: plan.id,
        title: t.title,
        planned_date: t.planned_date,
        estimated_minutes: t.estimated_minutes,
        stage_title: t.stage_title || undefined,
      });
    }

    router.push(`/plans/${plan.id}`);
  } catch (e: any) {
    error.value = e?.message || "创建失败";
  }
}
</script>

<template>
  <div class="plan-create-view">
    <header class="view-header">
      <h1>新建学习计划</h1>
      <button class="ghost-btn" @click="router.back()">取消</button>
    </header>

    <div v-if="error" class="error">{{ error }}</div>

    <section class="form-section">
      <h2>基本信息</h2>
      <label>
        <span class="label">标题</span>
        <input v-model="title" placeholder="一句话说清学什么" type="text" />
      </label>
      <label>
        <span class="label">目标</span>
        <textarea v-model="goal" placeholder="可空，详细描述" rows="2"></textarea>
      </label>
      <div class="row">
        <label>
          <span class="label">场景</span>
          <select v-model="scenario">
            <option value="worker">在职</option>
            <option value="student">学生</option>
            <option value="kaoyan">考研</option>
            <option value="cert">考证</option>
          </select>
        </label>
        <label>
          <span class="label">周数</span>
          <input v-model.number="weeks" type="number" min="1" max="52" />
        </label>
        <label>
          <span class="label">每周小时</span>
          <input v-model.number="weeklyHours" type="number" min="1" max="168" />
        </label>
      </div>
      <div class="row">
        <label>
          <span class="label">开始日期</span>
          <input v-model="startDate" type="date" />
        </label>
        <label>
          <span class="label">结束日期</span>
          <input :value="endDate" type="date" readonly />
        </label>
      </div>
    </section>

    <section class="form-section">
      <h2>任务列表</h2>
      <p class="hint">先手工加几个，验证 M1 流程。M3 上线后可以用 AI 自动拆解。</p>
      <div v-for="(task, idx) in draftTasks" :key="idx" class="draft-task">
        <input
          v-model="task.title"
          placeholder="任务标题"
          type="text"
          class="task-title-input"
        />
        <input v-model="task.planned_date" type="date" class="date-input" />
        <input
          v-model.number="task.estimated_minutes"
          type="number"
          min="5"
          max="600"
          placeholder="分钟"
          class="minutes-input"
        />
        <input
          v-model="task.stage_title"
          placeholder="阶段"
          class="stage-input"
        />
        <button class="ghost-btn remove-btn" @click="removeTask(idx)" type="button">×</button>
      </div>
      <button class="ghost-btn" @click="addTask" type="button">+ 添加任务</button>
    </section>

    <button class="submit-btn" @click="submit">创建</button>
  </div>
</template>

<style scoped>
.plan-create-view {
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
.error {
  padding: 8px 12px;
  background: #fcebeb;
  color: #c00;
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  font-size: 13px;
}
.form-section {
  background: #fff;
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid #eee;
  margin-bottom: 16px;
}
.form-section h2 {
  font-size: 14px;
  color: #534AB7;
  margin: 0 0 12px;
}
.form-section label {
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
}
.label {
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
}
input, textarea, select {
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
}
.row {
  display: flex;
  gap: 10px;
}
.row label {
  flex: 1;
}
.hint {
  font-size: 12px;
  color: #888;
  margin: 0 0 12px;
}
.draft-task {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.task-title-input { flex: 2; min-width: 120px; }
.date-input, .minutes-input, .stage-input { flex: 1; min-width: 80px; }
.remove-btn {
  padding: 0 8px;
  background: none;
  border: 1px solid #ddd;
  color: #c00;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.ghost-btn {
  background: none;
  border: 1px dashed #534AB7;
  color: #534AB7;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
}
.submit-btn {
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
</style>
