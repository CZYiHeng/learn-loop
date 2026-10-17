"""Task schemas — 每日任务的 I/O 模型。

关键设计（决策 3）：
- original_date / planned_date / completed_date 三日期分离
- 改期时 planned_date 变化、original_date 不变、shift_count+1
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# === 输入 ===

class TaskCreate(BaseModel):
    plan_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    planned_date: date  # 同时作为 original_date
    stage_title: Optional[str] = Field(None, max_length=100)
    stage_order: Optional[int] = Field(None, ge=0, le=100)
    estimated_minutes: int = Field(60, ge=5, le=600)
    priority: int = Field(3, ge=1, le=5)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    planned_date: Optional[date] = None
    stage_title: Optional[str] = Field(None, max_length=100)
    stage_order: Optional[int] = Field(None, ge=0, le=100)
    estimated_minutes: Optional[int] = Field(None, ge=5, le=600)
    priority: Optional[int] = Field(None, ge=1, le=5)
    actual_minutes: Optional[int] = Field(None, ge=0, le=1440)
    status: Optional[str] = Field(None, pattern="^(pending|done|skipped)$")


class TaskComplete(BaseModel):
    """完成 / 取消完成任务。"""
    actual_minutes: Optional[int] = Field(None, ge=0, le=1440)


class TaskReschedule(BaseModel):
    """改期。★ 决策 3：planned_date 变，original_date 不变，shift_count+1。"""
    new_date: date


class TaskBatchUpdate(BaseModel):
    """批量更新。"""
    task_ids: list[int] = Field(..., min_length=1, max_length=100)
    planned_date: Optional[date] = None
    stage_title: Optional[str] = None
    stage_order: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(pending|done|skipped)$")


class TaskBatchResult(BaseModel):
    """批量更新结果。"""
    updated: int
    failed: list[int] = []


# === 输出 ===

class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    title: str
    description: Optional[str] = None
    original_date: date
    planned_date: date
    completed_at: Optional[datetime] = None
    stage_title: Optional[str] = None
    stage_order: Optional[int] = None
    estimated_minutes: int
    actual_minutes: Optional[int] = None
    priority: int
    shift_count: int
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
