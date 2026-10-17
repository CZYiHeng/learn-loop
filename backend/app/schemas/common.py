"""通用 schemas — 分页响应等跨模块共用结构。

计划第五节统一分页：{items, total, page, page_size, has_next}
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
