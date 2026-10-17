"""review_card + review_log 两张表 — SM-2 复习。

关键设计（决策 13/14，评估后补充 ★）：
- state 字段（new/learning/review/relearning）★
- algorithm 版本标记 ★
- ef 下限 1.3
- 部分索引只索引 active 卡（next_review_date <= 当前）
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# 算法版本 — 升级时改这里，老数据通过 algorithm 字段识别
SM2_ALGORITHM_VERSION = "sm2-v1"
# 四档映射常量（决策 14）
# 重来=q1 / 困难=q2 / 良好=q4 / 简单=q5（无 q3 中间档）
QUALITY_MAP = {"again": 1, "hard": 2, "good": 4, "easy": 5}


class ReviewCard(Base, TimestampMixin):
    """SM-2 复习卡。"""

    __tablename__ = "review_card"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联任务（可选）— 从 task 生成复习卡时填
    task_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("task.id", ondelete="SET NULL"), nullable=True, index=True
    )
    plan_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("study_plan.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # 卡片内容
    front: Mapped[str] = mapped_column(Text, nullable=False, comment="正面/问题")
    back: Mapped[str] = mapped_column(Text, nullable=False, comment="背面/答案")
    tags: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # ★ 决策 13：状态机
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new", index=True,
        comment="new/learning/review/relearning",
    )
    # ★ 决策 13：算法版本标记
    algorithm: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SM2_ALGORITHM_VERSION,
    )

    # SM-2 核心字段
    ef: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.5,
        comment="ease factor，难度因子，下限 1.3",
    )
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lapses: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="失误次数",
    )
    next_review_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="下次到期日",
    )
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # 卡片是否被暂停（暂不复习）
    suspended: Mapped[bool] = mapped_column(default=False, nullable=False)

    logs: Mapped[list["ReviewLog"]] = relationship(
        "ReviewLog", back_populates="card", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('new', 'learning', 'review', 'relearning')",
            name="state_valid",
        ),
        CheckConstraint("ef >= 1.3", name="ef_floor"),
        CheckConstraint("interval_days >= 0", name="interval_nonneg"),
        CheckConstraint("repetitions >= 0", name="reps_nonneg"),
        CheckConstraint("lapses >= 0", name="lapses_nonneg"),
        # 部分索引延后到 M5 切 PG 时再加（SQLite 不接受字符串 WHERE）
    )

    def __repr__(self) -> str:
        return f"<ReviewCard {self.id} state={self.state} next={self.next_review_date}>"


class ReviewLog(Base, TimestampMixin):
    """复习日志 — 不是为查，是为可审计 + 事后调参（决策 13 注释）。"""

    __tablename__ = "review_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("review_card.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    # 用户评分：again / hard / good / easy
    rating: Mapped[str] = mapped_column(String(10), nullable=False)
    # 内部 q 值：1/2/4/5
    quality: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # 评分前快照
    before_ef: Mapped[float] = mapped_column(Float, nullable=False)
    before_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    before_repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    # 评分后状态
    after_ef: Mapped[float] = mapped_column(Float, nullable=False)
    after_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    after_repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    after_state: Mapped[str] = mapped_column(String(20), nullable=False)
    # 用时（秒）— 每日摩擦预算 ≤5 分钟验收用
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    card: Mapped["ReviewCard"] = relationship("ReviewCard", back_populates="logs")

    __table_args__ = (
        CheckConstraint(
            "rating IN ('again', 'hard', 'good', 'easy')", name="rating_valid"
        ),
        CheckConstraint("quality IN (1, 2, 4, 5)", name="quality_valid"),
    )

    def __repr__(self) -> str:
        return f"<ReviewLog card={self.card_id} rating={self.rating} @{self.reviewed_at}>"
