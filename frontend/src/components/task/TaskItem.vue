<script setup lang="ts">
// TaskItem — 任务卡片
// ★ 决策 10：勾选框放卡片左侧（拇指从右下伸向左上，勾选是最高频操作）
// ★ 乐观更新：点击勾选立即更新 UI，失败回滚
import { computed } from "vue";
import type { Task } from "@/api/types";

const props = defineProps<{
  task: Task;
}>();

const emit = defineEmits<{
  (e: "toggle", id: number): void;
  (e: "reschedule", id: number, newDate: string): void;
  (e: "delete", id: number): void;
}>();

const isDone = computed(() => props.task.status === "done");

function handleToggle() {
  if (isDone.value) {
    // 已完成，取消完成
    emit("toggle", props.task.id);
  } else {
    emit("toggle", props.task.id);
  }
}

function formatDate(s: string | null): string {
  if (!s) return "";
  return s.slice(0, 10);
}
</script>

<template>
  <div class="task-item" :class="{ done: isDone }">
    <!-- ★ 勾选框左侧 -->
    <button
      class="checkbox touchable"
      :class="{ checked: isDone }"
      @click="handleToggle"
      :aria-label="isDone ? '取消完成' : '完成任务'"
      type="button"
    >
      <span v-if="isDone">✓</span>
    </button>

    <div class="content">
      <div class="title">{{ task.title }}</div>
      <div class="meta">
        <span v-if="task.stage_title" class="stage">{{ task.stage_title }}</span>
        <span class="duration">{{ task.estimated_minutes }} 分钟</span>
        <span v-if="task.shift_count > 0" class="shift" :title="`原计划 ${formatDate(task.original_date)}`">
          📅 改期 ×{{ task.shift_count }}
        </span>
      </div>
    </div>

    <div class="actions">
      <!-- M2 会加 reschedule 入口；M1 暂只做完成/删除 -->
      <button
        class="action-btn touchable"
        @click="emit('delete', task.id)"
        aria-label="删除"
        type="button"
        title="删除"
      >
        ×
      </button>
    </div>
  </div>
</template>

<style scoped>
.task-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: var(--radius-md);
  transition: opacity 0.15s;
}
.task-item.done {
  opacity: 0.55;
}
.task-item.done .title {
  text-decoration: line-through;
  color: #888;
}

.checkbox {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: 2px solid #534AB7;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #fff;
  transition: all 0.15s;
  margin-top: 2px;
  padding: 0;
}
.checkbox.checked {
  background: #534AB7;
  border-color: #534AB7;
}

.content {
  flex: 1;
  min-width: 0;
}
.title {
  font-size: 15px;
  line-height: 1.4;
  color: #1a1a1a;
  margin-bottom: 4px;
  word-break: break-word;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #888;
}
.stage {
  background: #f0f0f5;
  padding: 1px 6px;
  border-radius: 4px;
}
.shift {
  color: #ba7517;
}

.actions {
  flex-shrink: 0;
}
.action-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: #ccc;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  line-height: 1;
}
.action-btn:hover {
  color: #c00;
}
</style>
