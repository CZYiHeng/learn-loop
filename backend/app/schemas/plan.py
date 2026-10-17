"""Plan schemas — 学习计划的 I/O 模型。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# === 输入 ===

class StudyPlanCreate(BaseModel):
    """手工创建计划（M1 用）。AI 生成走 /plans/generate（M3）。"""
    title: str = Field(..., min_length=1, max_length=200)
    goal: Optional[str] = None
    scenario: Literal["student", "worker", "kaoyan", "cert"] = "worker"
    origin: Literal["ai", "manual"] = "manual"
    weeks: int = Field(4, ge=1, le=52)
    weekly_hours: int = Field(8, ge=1, le=168)
    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, v: date, info) -> date:
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date 必须晚于 start_date")
        return v


class StudyPlanUpdate(BaseModel):
    """部分更新。所有字段可选。"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    goal: Optional[str] = None
    scenario: Optional[Literal["student", "worker", "kaoyan", "cert"]] = None
    status: Optional[Literal["draft", "active", "archived", "abandoned"]] = None
    weeks: Optional[int] = Field(None, ge=1, le=52)
    weekly_hours: Optional[int] = Field(None, ge=1, le=168)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


# === 输出 ===

class StudyPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    goal: Optional[str] = None
    scenario: str
    origin: str
    weeks: int
    weekly_hours: int
    start_date: date
    end_date: date
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlanProgress(BaseModel):
    """计划进度 — 由 task 聚合得到，不冗余在 plan 上（决策 1）。"""
    plan_id: int
    total_tasks: int
    completed_tasks: int
    skipped_tasks: int
    pending_tasks: int
    completion_rate: float  # 0-1
    on_time_rate: float  # 按原计划日期完成的比例
    stages: list[dict]  # [{stage_title, stage_order, total, completed, ...}]
