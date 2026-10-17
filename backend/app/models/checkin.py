"""task + checkin 两张表 — 每日任务 + 每日打卡。

关键设计（决策 2-6）：
- task.original_date 与 planned_date 分离（★ 决策 3）
- 状态用 varchar + CHECK 不用 PG ENUM（避开 Alembic 迁移坑）
- checkin 不冗余 task 状态
- 完成 task 自动打卡（service 层）
- 连续天数今天无活动不归零（service 层 + 单测）
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Task(Base, TimestampMixin):
    """每日任务（最核心表）。"""

    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("study_plan.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ★ 决策 3：三日期分离
    original_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
        comment="原计划日期，统计完成率用",
    )
    planned_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
        comment="当前计划日期，日历显示用，改期后变",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="完成时间戳，null = 未完成",
    )

    # ★ 决策 2：阶段不单独建表
    stage_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    stage_order: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # 时长（分钟）
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 优先级 1-5
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    # 推迟次数（统计用）
    shift_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 状态：pending / done / skipped
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)

    plan: Mapped["StudyPlan"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StudyPlan", back_populates="tasks"
    )

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'done', 'skipped')", name="status_valid"),
        CheckConstraint("priority >= 1 AND priority <= 5", name="priority_range"),
        CheckConstraint("estimated_minutes >= 5 AND estimated_minutes <= 600", name="est_minutes_range"),
        CheckConstraint("shift_count >= 0", name="shift_count_nonneg"),
    )

    def __repr__(self) -> str:
        return f"<Task {self.id} {self.title!r} @ {self.planned_date}>"


class Checkin(Base, TimestampMixin):
    """每日打卡。决策 4：不冗余 task 状态。

    一天一条（unique(date)），完成 task 时 service 层 upsert source='auto'。
    """

    __tablename__ = "checkin"
    __table_args__ = (
        UniqueConstraint("date", name="one_per_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True, unique=True)

    # 用户主动打卡 vs 完成任务自动打卡
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="auto")
    # 学习时长（分钟）— 碎片学习无法从 task 推导，必须单独存
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 心情备注
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 心情打分 1-5
    mood: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint("date", name="one_per_day"),
        CheckConstraint("source IN ('auto', 'manual')", name="source_valid"),
        CheckConstraint("duration_minutes IS NULL OR (duration_minutes >= 0 AND duration_minutes <= 1440)", name="duration_range"),
        CheckConstraint("mood IS NULL OR (mood >= 1 AND mood <= 5)", name="mood_range"),
    )

    def __repr__(self) -> str:
        return f"<Checkin {self.date} {self.source}>"
