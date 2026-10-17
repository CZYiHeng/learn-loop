"""分页 — 统一约定（计划第五节）。

前端拿到的格式：
    {
        "items": [...],
        "total": 123,
        "page": 1,
        "page_size": 20,
        "has_next": true
    }
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query


@dataclass
class PageParams:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def page_params(
    page: int = Query(1, ge=1, description="页码，从 1 起"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数，1-100"),
) -> PageParams:
    """依赖：从 query 解析分页参数。"""
    return PageParams(page=page, page_size=page_size)


def paginate(items: list, total: int, params: PageParams) -> dict:
    """组装分页响应体。"""
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "has_next": (params.offset + params.page_size) < total,
    }
