"""Plan service — 学习计划 CRUD + 进度聚合。

★ 决策 1：进度不冗余在 plan 上，由 task 聚合得到。
★ 决策 2：阶段不单独建表（stage_title + stage_order 在 task 上）。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.pagination import PageParams, paginate
from app.models.checkin import Task
from app.models.plan import StudyPlan
from app.schemas.plan import StudyPlanCreate, StudyPlanUpdate, PlanProgress


class PlanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: StudyPlanCreate) -> StudyPlan:
        plan = StudyPlan(
            title=payload.title,
            goal=payload.goal,
            scenario=payload.scenario,
            origin=payload.origin,
            weeks=payload.weeks,
            weekly_hours=payload.weekly_hours,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status="active",
        )
        self.db.add(plan)
        await self.db.flush()
        return plan

    async def get(self, plan_id: int) -> Optional[StudyPlan]:
        stmt = select(StudyPlan).where(StudyPlan.id == plan_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update(self, plan_id: int, payload: StudyPlanUpdate) -> StudyPlan:
        plan = await self.get(plan_id)
        if not plan:
            raise NotFoundError(f"plan {plan_id} not found")
        update_data = payload.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(plan, field, val)
        await self.db.flush()
        return plan

    async def delete(self, plan_id: int) -> bool:
        plan = await self.get(plan_id)
        if not plan:
            return False
        await self.db.delete(plan)
        await self.db.flush()
        return True

    async def list(self, params: PageParams, *, status: Optional[str] = None) -> dict:
        stmt = select(StudyPlan)
        if status:
            stmt = stmt.where(StudyPlan.status == status)
        stmt = stmt.order_by(StudyPlan.created_at.desc())

        # count
        count_stmt = select(func.count()).select_from(StudyPlan)
        if status:
            count_stmt = count_stmt.where(StudyPlan.status == status)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(params.offset).limit(params.limit)
        items = list((await self.db.execute(stmt)).scalars())
        return paginate(items, total, params)

    async def get_progress(self, plan_id: int) -> PlanProgress:
        """★ 决策 1：进度由 task 聚合得到。

        完成率：completed / (total - skipped)
        准时率：completed 中 completed_at <= original_date 的比例
        """
        plan = await self.get(plan_id)
        if not plan:
            raise NotFoundError(f"plan {plan_id} not found")

        tasks = await self._list_all_tasks(plan_id)
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "done")
        skipped = sum(1 for t in tasks if t.status == "skipped")
        pending = sum(1 for t in tasks if t.status == "pending")

        effective = total - skipped
        completion_rate = (completed / effective) if effective > 0 else 0.0

        # 准时率：完成日期 <= 原计划日期
        on_time = sum(
            1 for t in tasks
            if t.status == "done" and t.completed_at and t.completed_at.date() <= t.original_date
        )
        on_time_rate = (on_time / completed) if completed > 0 else 0.0

        # ★ 决策 2：阶段分组用一条 SQL 的 GROUP BY 思路实现
        stages = self._group_by_stage(tasks)

        return PlanProgress(
            plan_id=plan_id,
            total_tasks=total,
            completed_tasks=completed,
            skipped_tasks=skipped,
            pending_tasks=pending,
            completion_rate=round(completion_rate, 4),
            on_time_rate=round(on_time_rate, 4),
            stages=stages,
        )

    async def _list_all_tasks(self, plan_id: int) -> list[Task]:
        stmt = select(Task).where(Task.plan_id == plan_id).order_by(
            Task.stage_order, Task.planned_date
        )
        return list((await self.db.execute(stmt)).scalars())

    def _group_by_stage(self, tasks: list[Task]) -> list[dict]:
        """★ 决策 2：用纯 Python GROUP BY 模拟，不引第二张表。"""
        groups: dict[tuple[str, int], list[Task]] = {}
        for t in tasks:
            key = (t.stage_title or "未分组", t.stage_order if t.stage_order is not None else 0)
            groups.setdefault(key, []).append(t)

        result = []
        for (title, order), group in sorted(groups.items(), key=lambda x: x[0][1]):
            completed = sum(1 for t in group if t.status == "done")
            total = len(group)
            result.append({
                "stage_title": title,
                "stage_order": order,
                "total": total,
                "completed": completed,
                "completion_rate": round(completed / total, 4) if total > 0 else 0.0,
            })
        return result
