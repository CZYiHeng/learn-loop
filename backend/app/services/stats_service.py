"""Stats service — 今日看板聚合。

一次请求拿到：今日任务 + 任务汇总 + 打卡状态 + streak。
前端不必发多个请求。
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkin import Checkin
from app.schemas.stats import TodayStats, TaskSummary
from app.services.checkin_service import CheckinService
from app.services.task_service import TaskService


class StatsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_service = TaskService(db)
        self.checkin_service = CheckinService(db)

    async def get_today(self, today: Optional[date] = None) -> TodayStats:
        if today is None:
            from app.services.checkin_service import _today_local
            today = _today_local()

        # 1. 今日任务（按 planned_date 取，决策 3）
        tasks = await self.task_service.list_by_date(today)

        # 2. 任务汇总
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "done")
        skipped = sum(1 for t in tasks if t.status == "skipped")
        pending = sum(1 for t in tasks if t.status == "pending")
        est_total = sum(t.estimated_minutes for t in tasks)
        actual_total = sum(t.actual_minutes or 0 for t in tasks if t.status == "done")

        effective = total - skipped
        completion_rate = (completed / effective) if effective > 0 else 0.0

        summary = TaskSummary(
            total=total,
            completed=completed,
            skipped=skipped,
            pending=pending,
            completion_rate=round(completion_rate, 4),
            estimated_minutes_total=est_total,
            actual_minutes_total=actual_total,
        )

        # 3. 打卡状态
        checkin = await self.checkin_service.get(today)

        # 4. streak
        streak_data = await self.checkin_service.get_streak(today=today)

        # 5. 任务输出 — 简化为前端可用的字典
        tasks_out = [
            {
                "id": t.id,
                "plan_id": t.plan_id,
                "title": t.title,
                "description": t.description,
                "planned_date": str(t.planned_date),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "stage_title": t.stage_title,
                "stage_order": t.stage_order,
                "estimated_minutes": t.estimated_minutes,
                "actual_minutes": t.actual_minutes,
                "priority": t.priority,
                "shift_count": t.shift_count,
                "status": t.status,
            }
            for t in tasks
        ]

        checkin_out = None
        if checkin:
            checkin_out = {
                "id": checkin.id,
                "date": str(checkin.date),
                "source": checkin.source,
                "duration_minutes": checkin.duration_minutes,
                "note": checkin.note,
                "mood": checkin.mood,
            }

        return TodayStats(
            date=today,
            tasks=tasks_out,
            task_summary=summary,
            checkin=checkin_out,
            streak=streak_data.streak,
            today_active=streak_data.today_active,
            last_active_date=streak_data.last_active_date,
        )
