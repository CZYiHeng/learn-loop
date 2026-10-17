"""study_plan 表 — 学习计划主体（决策 1：进度不冗余，由 task 聚合）。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class StudyPlan(Base, TimestampMixin):
    __tablename__ = "study_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 计划标题（一句话，来自用户输入或 AI 生成）
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 用户输入的原始目标（"一个月入门 LangGraph"），AI 生成场景下保留
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 场景：student / worker / kaoyan / cert
    scenario: Mapped[str] = mapped_column(String(20), nullable=False, default="worker")
    # 来源：ai 生成 / 手工
    origin: Mapped[str] = mapped_column(
        String(10), nullable=False, default="manual"
    )
    # 总周数
    weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    # 每周可学小时
    weekly_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    # 起止日期
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # 软状态：draft / active / archived / abandoned
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )

    # 关联任务（一对多）。前向引用 "Task" 字符串由 SQLAlchemy 在 metadata 注册时解析。
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("origin IN ('ai', 'manual')", name="origin_valid"),
        CheckConstraint(
            "scenario IN ('student', 'worker', 'kaoyan', 'cert')", name="scenario_valid"
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived', 'abandoned')",
            name="status_valid",
        ),
        CheckConstraint("weeks > 0 AND weeks <= 52", name="weeks_range"),
        CheckConstraint("weekly_hours > 0 AND weekly_hours <= 168", name="weekly_hours_range"),
    )

    def __repr__(self) -> str:
        return f"<StudyPlan {self.id} {self.title!r}>"
