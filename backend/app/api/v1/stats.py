"""Stats 路由 — 今日看板聚合。"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_user
from app.schemas.stats import TodayStats
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/today", response_model=TodayStats, summary="今日看板（聚合接口）")
async def get_today_stats(
    today: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    """一次请求拿全：今日任务 + 任务汇总 + 打卡状态 + streak。"""
    svc = StatsService(db)
    return await svc.get_today(today=today)
