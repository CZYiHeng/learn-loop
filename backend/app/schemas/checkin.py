"""Checkin schemas — 每日打卡 + streak。

★ 决策 4：checkin 表不冗余 task 状态。
★ 决策 5：完成 task 自动打卡（service 层）。
★ 决策 6：streak 今天无活动不归零（service 层 + 单测覆盖）。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CheckinCreate(BaseModel):
    """用户主动打卡。完成 task 时不走这条接口，由 task_service 自动 upsert。"""
    date: date
    duration_minutes: Optional[int] = Field(None, ge=0, le=1440)
    note: Optional[str] = Field(None, max_length=2000)
    mood: Optional[int] = Field(None, ge=1, le=5)


class CheckinUpdate(BaseModel):
    duration_minutes: Optional[int] = Field(None, ge=0, le=1440)
    note: Optional[str] = Field(None, max_length=2000)
    mood: Optional[int] = Field(None, ge=1, le=5)


class CheckinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    source: str  # 'auto' / 'manual'
    duration_minutes: Optional[int] = None
    note: Optional[str] = None
    mood: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Streak(BaseModel):
    """连续学习天数 —★ 决策 6 的核心输出。

    streak：连续活跃天数。今天或昨天有活动 → 不归零，按最末活跃日往前数。
    today_active：今天是否活跃（用于 UI 提示）。
    last_active_date：最后活跃日（用于断签提示）。
    """
    streak: int
    today_active: bool
    last_active_date: Optional[date] = None
    total_active_days: int = 0  # 历史总活跃天数
