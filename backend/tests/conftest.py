"""pytest 共享夹具。"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base


@pytest_asyncio.fixture
async def memory_db():
    """每个测试用独立的内存 SQLite，隔离干净。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def today():
    """统一用 2026-10-17 当今天，避免时区坑。"""
    from datetime import date
    return date(2026, 10, 17)


@pytest.fixture(autouse=True)
def _no_settings_warning():
    """关闭 Settings 验证警告。"""
    pass
