// task store — ★ 乐观更新（M1 验收要点）
// 用户点击勾选后立即更新 UI，不等 API 返回；失败回滚。
import { defineStore } from "pinia";
import { ref } from "vue";
import { tasksApi } from "@/api/tasks";
import type { Task } from "@/api/types";

export const useTaskStore = defineStore("task", () => {
  // 状态
  const tasks = ref<Task[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // 今日任务（按 planned_date 查）
  async function loadToday(date: string) {
    loading.value = true;
    error.value = null;
    try {
      tasks.value = await tasksApi.list({ planned_date: date });
    } catch (e: any) {
      error.value = e?.message || "加载失败";
    } finally {
      loading.value = false;
    }
  }

  // ★ 乐观更新：完成 / 取消完成
  // 1. 先把本地状态改了，UI 立刻反馈
  // 2. 再发请求，失败回滚
  async function completeTask(taskId: number, actualMinutes?: number) {
    const task = tasks.value.find((t) => t.id === taskId);
    if (!task) return;

    // 保存原始状态以便回滚
    const original = { status: task.status, completed_at: task.completed_at, actual_minutes: task.actual_minutes };

    // 立刻更新 UI（乐观）
    task.status = "done";
    task.completed_at = new Date().toISOString();
    if (actualMinutes !== undefined) {
      task.actual_minutes = actualMinutes;
    }

    try {
      const updated = await tasksApi.complete(taskId, actualMinutes);
      // 用服务端结果替换本地（防止本地时区有偏差）
      const idx = tasks.value.findIndex((t) => t.id === taskId);
      if (idx >= 0) tasks.value[idx] = updated;
    } catch (e) {
      // 回滚
      task.status = original.status;
      task.completed_at = original.completed_at;
      task.actual_minutes = original.actual_minutes;
      error.value = "完成失败，已回滚";
      throw e;
    }
  }

  async function uncompleteTask(taskId: number) {
    const task = tasks.value.find((t) => t.id === taskId);
    if (!task) return;

    const original = { status: task.status, completed_at: task.completed_at, actual_minutes: task.actual_minutes };
    task.status = "pending";
    task.completed_at = null;
    task.actual_minutes = null;

    try {
      const updated = await tasksApi.uncomplete(taskId);
      const idx = tasks.value.findIndex((t) => t.id === taskId);
      if (idx >= 0) tasks.value[idx] = updated;
    } catch (e) {
      task.status = original.status;
      task.completed_at = original.completed_at;
      task.actual_minutes = original.actual_minutes;
      throw e;
    }
  }

  // ★ 乐观更新：改期
  async function rescheduleTask(taskId: number, newDate: string) {
    const task = tasks.value.find((t) => t.id === taskId);
    if (!task) return;

    const original = { planned_date: task.planned_date, shift_count: task.shift_count };
    task.planned_date = newDate;
    task.shift_count += 1;

    try {
      const updated = await tasksApi.reschedule(taskId, newDate);
      // 如果新日期不是今天，从今日列表移除
      const today = new Date().toISOString().slice(0, 10);
      if (newDate !== today) {
        tasks.value = tasks.value.filter((t) => t.id !== taskId);
      } else {
        const idx = tasks.value.findIndex((t) => t.id === taskId);
        if (idx >= 0) tasks.value[idx] = updated;
      }
    } catch (e) {
      task.planned_date = original.planned_date;
      task.shift_count = original.shift_count;
      throw e;
    }
  }

  async function createTask(payload: Parameters<typeof tasksApi.create>[0]) {
    const task = await tasksApi.create(payload);
    // 如果是今天的任务，加到列表
    const today = new Date().toISOString().slice(0, 10);
    if (payload.planned_date === today) {
      tasks.value.push(task);
    }
    return task;
  }

  async function deleteTask(taskId: number) {
    await tasksApi.delete(taskId);
    tasks.value = tasks.value.filter((t) => t.id !== taskId);
  }

  function clear() {
    tasks.value = [];
    error.value = null;
  }

  return {
    tasks,
    loading,
    error,
    loadToday,
    completeTask,
    uncompleteTask,
    rescheduleTask,
    createTask,
    deleteTask,
    clear,
  };
});
