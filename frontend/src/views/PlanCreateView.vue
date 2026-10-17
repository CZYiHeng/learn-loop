<script setup lang="ts">
// PlanCreateView — 改造为 AI 生成入口（修订 electric-pulse）
// 输入目标 + 场景 → 自动生成任务 → 直接跳今日看板
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/api/client";

const router = useRouter();

const goal = ref("");
const scenario = ref<"student" | "worker" | "kaoyan" | "cert">("worker");
const generating = ref(false);
const progressText = ref("");
const error = ref<string>("");

const scenarios = [
  { value: "worker", label: "在职", desc: "每周 5-8h，周中晚上 + 周末" },
  { value: "student", label: "学生", desc: "每周 15-20h，每天 2-3h" },
  { value: "kaoyan", label: "考研", desc: "每周 25-30h，长周期 8-12 周" },
  { value: "cert", label: "考证", desc: "按考试日倒推，每天 1-2h" },
] as const;

const canSubmit = computed(() => goal.value.trim().length > 0 && !generating.value);

// 三阶段文字轮播
let progressTimer: number | null = null;
function startProgressAnimation() {
  const stages = [
    "🤔 理解目标…",
    "📋 拆解阶段…",
    "📅 排每日任务…",
    "✨ 整理输出…",
  ];
  let i = 0;
  progressText.value = stages[0];
  progressTimer = window.setInterval(() => {
    i = (i + 1) % stages.length;
    progressText.value = stages[i];
  }, 1500);
}

function stopProgressAnimation() {
  if (progressTimer !== null) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

async function submit() {
  if (!canSubmit.value) return;
  generating.value = true;
  error.value = "";
  startProgressAnimation();

  try {
    const resp = await api.post<{ generation_id: number; plan_id: number; status: string }>(
      "/plans/generate",
      {
        goal: goal.value.trim(),
        scenario: scenario.value,
      },
      { timeout: 120000 }  // 60s 生成 + 缓冲
    );
    stopProgressAnimation();
    if (resp.plan_id) {
      // ★ 修订：生成完成直接进今日看板，顶部横幅后续做
      router.push("/today");
    }
  } catch (e: any) {
    stopProgressAnimation();
    error.value = e?.message || "生成失败，请稍后重试";
  } finally {
    generating.value = false;
  }
}
</script>

<template>
  <div class="plan-create-view">
    <header class="view-header">
      <button class="ghost-btn" @click="router.back()">←</button>
      <h1>新建学习计划</h1>
    </header>

    <div v-if="error" class="error">{{ error }}</div>

    <!-- 生成中遮罩 -->
    <div v-if="generating" class="generating-overlay">
      <div class="generating-card">
        <div class="spinner"></div>
        <div class="progress-text">{{ progressText }}</div>
        <p class="hint">AI 正在为你拆解计划，预计 30-60 秒</p>
      </div>
    </div>

    <section class="form-section">
      <label class="goal-input">
        <span class="label">学习目标</span>
        <textarea
          v-model="goal"
          placeholder="一句话说清想学什么，如：一个月入门 LangGraph"
          rows="3"
          :disabled="generating"
        ></textarea>
      </label>

      <div class="scenarios">
        <span class="label">场景</span>
        <div class="scenario-options">
          <label
            v-for="s in scenarios"
            :key="s.value"
            class="scenario-option"
            :class="{ active: scenario === s.value }"
          >
            <input
              type="radio"
              v-model="scenario"
              :value="s.value"
              :disabled="generating"
            />
            <div class="scenario-label">{{ s.label }}</div>
            <div class="scenario-desc">{{ s.desc }}</div>
          </label>
        </div>
      </div>

      <button
        class="submit-btn touchable"
        :disabled="!canSubmit"
        @click="submit"
      >
        {{ generating ? "生成中…" : "✨ 让 AI 安排任务" }}
      </button>

      <p class="footnote">
        提交后将自动拆解为阶段和每日任务，直接进入今日看板。
      </p>
    </section>
  </div>
</template>

<style scoped>
.plan-create-view {
  padding: 16px;
  max-width: 720px;
  margin: 0 auto;
  position: relative;
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
.error {
  padding: 10px 14px;
  background: #fcebeb;
  color: #c00;
  border-radius: var(--radius-md);
  margin-bottom: 12px;
  font-size: 13px;
}

.generating-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.generating-card {
  background: #fff;
  padding: 32px 40px;
  border-radius: var(--radius-lg);
  text-align: center;
  min-width: 280px;
}
.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #eee;
  border-top-color: #534AB7;
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.progress-text {
  font-size: 16px;
  color: #1a1a1a;
  margin-bottom: 8px;
  font-weight: 500;
}
.hint {
  font-size: 12px;
  color: #888;
  margin: 0;
}

.form-section {
  background: #fff;
  padding: 20px;
  border-radius: var(--radius-md);
  border: 1px solid #eee;
}
.goal-input {
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
}
.label {
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
  display: block;
}
textarea {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-family: inherit;
  resize: vertical;
}

.scenarios {
  margin-bottom: 24px;
}
.scenario-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.scenario-option {
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: block;
  position: relative;
  transition: all 0.15s;
}
.scenario-option.active {
  border-color: #534AB7;
  background: #f0f0f5;
}
.scenario-option input {
  position: absolute;
  opacity: 0;
}
.scenario-label {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
}
.scenario-desc {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
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
  transition: opacity 0.15s;
}
.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.footnote {
  font-size: 12px;
  color: #888;
  text-align: center;
  margin: 12px 0 0;
}
</style>
