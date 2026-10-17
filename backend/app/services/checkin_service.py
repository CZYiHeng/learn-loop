"""Checkin service — 打卡 + streak 计算（★ 决策 4/5/6）。

★ 决策 4：checkin 表不冗余 task 状态。checkin 一天一条（unique(date)）。
★ 决策 5：完成 task 时 service 层 upsert checkin source='auto'。
★ 决策 6：streak 今天无活动按「最后活跃日是今天或昨天」算，不归零。

streak 算法：
    活跃日 = checkin.date ∪ task.completed_at.date()
    - 今天活跃 → streak_end = 今天
    - 今天无活动但昨天活跃 → streak_end = 昨天
    - 否则 → streak = 0（断了）

    从 streak_end 往前数连续活跃天数，遇到不活跃日就停。

★ 关键测试用例（必须覆盖）：
    - 昨天活跃、今天没动 → streak 仍显示 N（不归零）
    - 前天活跃、昨天今天都没动 → streak = 0
    - 今天活跃、昨天不活跃 → streak = 1
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.checkin import Checkin, Task
from app.models.plan import StudyPlan
from app.schemas.checkin import CheckinCreate, CheckinUpdate, CheckinOut, Streak


def _today_local() -> date:
    """按 Asia/Shanghai 时区取今天。绝不用 utcnow()（决策 7.x）。"""
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo
    return _dt.now(ZoneInfo(settings.timezone if hasattr(settings, "timezone") else "Asia/Shanghai")).date()


class CheckinService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_for_date(
        self, d: date, *, source: str = "auto"
    ) -> Checkin:
        """决策 5：完成 task 时自动 upsert checkin。

        source='auto' 表示自动创建（用户没主动打卡但有活动）。
        若当天已有 checkin，不动 source；否则创建。
        """
        stmt = select(Checkin).where(Checkin.date == d)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing
        checkin = Checkin(date=d, source=source)
        self.db.add(checkin)
        await self.db.flush()
        return checkin

    async def upsert(self, payload: CheckinCreate) -> Checkin:
        """用户主动打卡：当天已有 → 更新；否则创建 source='manual'。"""
        stmt = select(Checkin).where(Checkin.date == payload.date)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            # 不覆盖 source='manual' 为 auto，但 auto 可被升级为 manual
            existing.source = "manual"
            existing.duration_minutes = payload.duration_minutes
            existing.note = payload.note
            existing.mood = payload.mood
            await self.db.flush()
            return existing
        checkin = Checkin(
            date=payload.date,
            source="manual",
            duration_minutes=payload.duration_minutes,
            note=payload.note,
            mood=payload.mood,
        )
        self.db.add(checkin)
        await self.db.flush()
        return checkin

    async def update(self, d: date, payload: CheckinUpdate) -> Optional[Checkin]:
        stmt = select(Checkin).where(Checkin.date == d)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if not existing:
            return None
        for field, val in payload.model_dump(exclude_unset=True).items():
            setattr(existing, field, val)
        await self.db.flush()
        return existing

    async def delete(self, d: date) -> bool:
        stmt = select(Checkin).where(Checkin.date == d)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if not existing:
            return False
        await self.db.delete(existing)
        await self.db.flush()
        return True

    async def get(self, d: date) -> Optional[Checkin]:
        stmt = select(Checkin).where(Checkin.date == d)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_range(self, start: date, end: date) -> list[Checkin]:
        stmt = (
            select(Checkin)
            .where(Checkin.date >= start, Checkin.date <= end)
            .order_by(Checkin.date)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def get_streak(self, today: Optional[date] = None) -> Streak:
        """★ 决策 6 的核心实现。

        算法：
            1. 取所有活跃日（checkin.date ∪ task.completed_at 的日期部分）
            2. 决定 streak_end：
               - 今天在活跃日集合 → streak_end = today
               - 今天不在但昨天在 → streak_end = yesterday
               - 都不在 → streak = 0
            3. 从 streak_end 往前数连续活跃天数
        """
        if today is None:
            today = _today_local()

        # 拿所有 checkin.date
        checkin_dates_stmt = select(Checkin.date)
        checkin_dates = set((await self.db.execute(checkin_dates_stmt)).scalars())

        # 拿所有 task.completed_at 的日期部分（仅 done 状态）
        task_done_stmt = select(Task.completed_at).where(
            Task.completed_at.isnot(None)
        )
        task_done_at = (await self.db.execute(task_done_stmt)).scalars()
        task_done_dates = {dt.date() if dt else None for dt in task_done_at}
        task_done_dates.discard(None)

        active_dates = checkin_dates | task_done_dates
        if not active_dates:
            return Streak(streak=0, today_active=False, last_active_date=None, total_active_days=0)

        last_active = max(active_dates)

        # 决策 6：今天没动但昨天活跃 → 仍算 streak
        today_active = today in active_dates
        if today_active:
            streak_end = today
        elif (today - timedelta(days=1)) in active_dates:
            streak_end = today - timedelta(days=1)
        else:
            # 断了
            return Streak(
                streak=0,
                today_active=False,
                last_active_date=last_active,
                total_active_days=len(active_dates),
            )

        # 从 streak_end 往前数连续活跃天数
        streak = 0
        current = streak_end
        while current in active_dates:
            streak += 1
            current -= timedelta(days=1)

        return Streak(
            streak=streak,
            today_active=today_active,
            last_active_date=last_active,
            total_active_days=len(active_dates),
        )
