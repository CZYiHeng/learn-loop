"""健康检查路由 — M0 验收核心：/health 返回 OK + 迁移后表数。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="健康检查")
async def health(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    """返回应用状态 + 数据库连通性 + 表数量。

    M0 验收：迁移完成后应返回 db.table_count >= 10。
    """
    if settings.is_sqlite:
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        )
    else:
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema='public'"
            )
        )
    table_count = result.scalar() or 0

    response.headers["Cache-Control"] = "no-store"
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.env,
        "version": __import__("app").__version__,
        "db": {
            "driver": "sqlite" if settings.is_sqlite else "postgres",
            "table_count": table_count,
            "ok": table_count >= 10,
        },
    }
