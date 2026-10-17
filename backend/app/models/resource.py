"""resource + resource_chunk + file_object 三张表 — 资料库与 RAG。

设计要点：
- M5 启动时切 PG，再加 Vector 列 + pgvector 索引
- M0-M4 不需要，只建表结构，不动 embedding 字段
- content_hash 作 embedding 缓存键，避免重复 embedding 调用
- content_md（人看）与 plain_text（机器切块）分开存
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Resource(Base, TimestampMixin):
    """资料条目。"""

    __tablename__ = "resource"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 类型：note / link / doc / video / pdf
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="note", index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # 人看的原始 markdown
    content_md: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 机器切块用的纯文本
    plain_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 处理状态机
    process_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True,
        comment="pending/chunking/embedding/ready/failed",
    )
    process_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    process_finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    chunks: Mapped[list["ResourceChunk"]] = relationship(
        "ResourceChunk", back_populates="resource", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('note', 'link', 'doc', 'video', 'pdf')", name="type_valid"
        ),
        CheckConstraint(
            "process_status IN ('pending', 'chunking', 'embedding', 'ready', 'failed')",
            name="process_status_valid",
        ),
    )


class ResourceChunk(Base, TimestampMixin):
    """资料分块 — M5 启动时加 Vector 列与 pgvector 索引。

    M0-M4：先建表，embedding 列用 JSON 存（或干脆不填）。
    """

    __tablename__ = "resource_chunk"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resource.id", ondelete="CASCADE"), nullable=False, index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 标题路径，如 "第三章 > 3.2 内存模型 > 字段对齐"
    heading_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # 字符数（统计用）
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # ★ embedding 缓存键 — 换模型时识别脏数据
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # M0-M4：embedding 暂用 JSON 字符串；M5 切 PG 时改为 Vector(1024)
    embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    resource: Mapped["Resource"] = relationship("Resource", back_populates="chunks")

    __table_args__ = (
        Index("ix_resource_chunk_resource_index", "resource_id", "chunk_index", unique=True),
    )


class FileObject(Base, TimestampMixin):
    """上传文件 — sha256 去重。"""

    __tablename__ = "file_object"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # 存储路径（相对 uploads/）
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
