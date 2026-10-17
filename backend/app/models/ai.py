"""ai_generation + qa_conversation + qa_message 三张表 — AI 审计与问答。

设计要点：
- request_hash 幂等键（不含 client_request_id，决策第 12 节注释）
- repair_attempts 记录 LLM 重试次数
- token_usage 成本控制与计费审计
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# JSONB 跨库兼容：SQLAlchemy 的 JSON 在 SQLite 上是 TEXT，在 PG 上是 JSON/JSONB
# M5 切 PG 时若想显式 JSONB，可换 sqlalchemy.dialects.postgresql.JSONB


class AIGeneration(Base, TimestampMixin):
    """AI 生成审计 — 计划/出卡/扩展任务的生成记录。

    核心保护：
    - request_hash 幂等
    - status='failed' 时不会落 plan/task
    - 单事务落库保证表里不留半成品
    """

    __tablename__ = "ai_generation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 任务类型：plan / card / expand
    task_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # ★ 幂等键：sha256(目标+日期+参数+prompt_version)，不含 client_request_id
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True,
        comment="pending/running/succeeded/failed",
    )
    # 输入快照（含 goal + scenario + prompt_version）
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # 输出快照（结构化结果）
    response_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # ★ 失败重试次数（最多 2 次）
    repair_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # ★ token 用量审计
    token_usage: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # 用时（秒）
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 关联最终落库的 plan_id（仅 plan 类型）
    plan_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "task_type IN ('plan', 'card', 'expand')", name="task_type_valid"
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name="status_valid",
        ),
    )


class QAConversation(Base, TimestampMixin):
    """问答会话。"""

    __tablename__ = "qa_conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="新对话")
    resource_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("resource.id", ondelete="SET NULL"), nullable=True
    )
    # 会话元信息（model / embedding_model 版本）
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    messages: Mapped[list["QAMessage"]] = relationship(
        "QAMessage", back_populates="conversation", cascade="all, delete-orphan"
    )


class QAMessage(Base, TimestampMixin):
    """问答消息。"""

    __tablename__ = "qa_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("qa_conversation.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="user/assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # ★ 引用溯源
    citations: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # token 用量（assistant 角色）
    token_usage: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    conversation: Mapped["QAConversation"] = relationship(
        "QAConversation", back_populates="messages"
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="role_valid"),
    )
