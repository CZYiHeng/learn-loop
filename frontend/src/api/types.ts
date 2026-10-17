// API 类型定义 — 与后端 Pydantic schemas 对应
// 后端 schemas/ 目录下结构同此

export interface StudyPlan {
  id: number;
  title: string;
  goal: string | null;
  scenario: "student" | "worker" | "kaoyan" | "cert";
  origin: "ai" | "manual";
  weeks: number;
  weekly_hours: number;
  start_date: string;
  end_date: string;
  status: "draft" | "active" | "archived" | "abandoned";
  created_at: string | null;
  updated_at: string | null;
}

export interface Task {
  id: number;
  plan_id: number;
  title: string;
  description: string | null;
  original_date: string;  // ★ 决策 3：与 planned_date 分离
  planned_date: string;
  completed_at: string | null;
  stage_title: string | null;
  stage_order: number | null;
  estimated_minutes: number;
  actual_minutes: number | null;
  priority: number;
  shift_count: number;
  status: "pending" | "done" | "skipped";
  created_at: string | null;
  updated_at: string | null;
}

export interface Checkin {
  id: number;
  date: string;
  source: "auto" | "manual";
  duration_minutes: number | null;
  note: string | null;
  mood: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface Streak {
  streak: number;
  today_active: boolean;
  last_active_date: string | null;
  total_active_days: number;
}

export interface TaskSummary {
  total: number;
  completed: number;
  skipped: number;
  pending: number;
  completion_rate: number;
  estimated_minutes_total: number;
  actual_minutes_total: number;
}

export interface TodayStats {
  date: string;
  tasks: Task[];
  task_summary: TaskSummary;
  checkin: Checkin | null;
  streak: number;
  today_active: boolean;
  last_active_date: string | null;
}

export interface PlanProgress {
  plan_id: number;
  total_tasks: number;
  completed_tasks: number;
  skipped_tasks: number;
  pending_tasks: number;
  completion_rate: number;
  on_time_rate: number;
  stages: Array<{
    stage_title: string;
    stage_order: number;
    total: number;
    completed: number;
    completion_rate: number;
  }>;
}

export interface PageResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

// === 输入 DTO ===

export interface PlanCreateInput {
  title: string;
  goal?: string;
  scenario?: "student" | "worker" | "kaoyan" | "cert";
  origin?: "ai" | "manual";
  weeks?: number;
  weekly_hours?: number;
  start_date: string;
  end_date: string;
}

export interface TaskCreateInput {
  plan_id: number;
  title: string;
  description?: string;
  planned_date: string;
  stage_title?: string;
  stage_order?: number;
  estimated_minutes?: number;
  priority?: number;
}

export interface TaskRescheduleInput {
  new_date: string;
}

export interface CheckinCreateInput {
  date: string;
  duration_minutes?: number;
  note?: string;
  mood?: number;
}
