"""数据库引擎与会话。

设计要点：
- AsyncEngine + AsyncSession：FastAPI 异步生态友好
- SQLite 启用 WAL + 外键约束（默认 off，必须开）
- M5 切 PG 时：把 DATABASE_URL 改成 postgresql+asyncpg://...，其余不动
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# 全局引擎 — app lifespan 创建/销毁
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug and settings.env == "local",
    future=True,
    # SQLite 需要的额外参数
    **({"connect_args": {"check_same_thread": False}} if settings.is_sqlite else {}),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def engine_lifespan() -> AsyncGenerator[None, None]:
    """应用 lifespan：启动时打开 SQLite PRAGMA，退出时 dispose。

    DDL 全部由 alembic 管理；这里不自动建表，避免与迁移冲突。
    """
    # 本地 SQLite：开启外键 + WAL（提高并发、防止丢数据）
    if settings.is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(_apply_sqlite_pragmas)
    try:
        yield
    finally:
        await engine.dispose()


def _apply_sqlite_pragmas(conn) -> None:
    """SQLite 必须开启外键约束 + WAL 模式。"""
    if settings.is_sqlite:
        from sqlalchemy import text
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：每请求一个 session，请求结束自动关。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
