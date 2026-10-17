"""Stats schemas — 今日看板数据。"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class TaskSummary(BaseModel):
    total: int = 0
    completed: int = 0
    skipped: int = 0
    pending: int = 0
    completion_rate: float = 0.0  # 0-1
    estimated_minutes_total: int = 0
    actual_minutes_total: int = 0


class TodayStats(BaseModel):
    """今日看板需要的数据。

    一次请求拿全：今日任务列表 + 打卡状态 + streak + 今日汇总。
    前端不必发多个请求。
    """
    date: date
    tasks: list[dict] = []  # TaskOut 的简化版（前端可直接用）
    task_summary: TaskSummary
    checkin: Optional[dict] = None  # CheckinOut 或 None
    streak: int = 0
    today_active: bool = False
    last_active_date: Optional[date] = None
