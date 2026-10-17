"""setting 表 — 用户设置（key-value）。

一期单用户不需要 user_id 外键。M6 切小程序时再加。
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Setting(Base, TimestampMixin):
    """键值设置。

    设计：value 用 JSON 存所有类型，避免多列。
    常用键：
      - daily_new_card_limit  (int)       默认 10
      - daily_review_limit    (int)       默认 50
      - review_algorithm      (str)       sm2-v1
      - timezone              (str)       Asia/Shanghai
      - workdays              (list[str]) 周一~周五
      - llm_provider          (str)       deepseek
    """

    __tablename__ = "setting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Setting {self.key}={self.value}>"
