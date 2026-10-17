"""Task service — 每日任务核心业务逻辑。

★ 决策 3：original_date 与 planned_date 分离
   - 创建时：original_date = planned_date
   - 改期时：planned_date = new_date, original_date 不变, shift_count += 1
   - 统计完成率用 original_date
   - 日历显示用 planned_date

★ 决策 5：完成 task 时自动 upsert checkin source='auto'
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.models.checkin import Checkin, Task
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskComplete, TaskReschedule,
    TaskBatchUpdate, TaskBatchResult,
)
from app.services.checkin_service import CheckinService


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.checkin_service = CheckinService(db)

    async def create(self, payload: TaskCreate) -> Task:
        """创建任务。original_date = planned_date（决策 3）。"""
        task = Task(
            plan_id=payload.plan_id,
            title=payload.title,
            description=payload.description,
            original_date=payload.planned_date,  # ★ 初始一致
            planned_date=payload.planned_date,
            stage_title=payload.stage_title,
            stage_order=payload.stage_order,
            estimated_minutes=payload.estimated_minutes,
            priority=payload.priority,
            status="pending",
            shift_count=0,
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def get(self, task_id: int) -> Optional[Task]:
        stmt = select(Task).where(Task.id == task_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update(self, task_id: int, payload: TaskUpdate) -> Task:
        task = await self.get(task_id)
        if not task:
            raise NotFoundError(f"task {task_id} not found")

        update_data = payload.model_dump(exclude_unset=True)
        # 改 planned_date 时不动 original_date（决策 3）
        # 但要注意：如果是用户主动改 planned_date，应该走 /reschedule 接口走 shift_count
        if "planned_date" in update_data and update_data["planned_date"] != task.planned_date:
            raise ValidationError(
                "改期请走 POST /tasks/{id}/reschedule，不要直接 PATCH planned_date",
                details={"task_id": task_id},
            )

        for field, val in update_data.items():
            setattr(task, field, val)
        await self.db.flush()
        return task

    async def complete(
        self, task_id: int, payload: Optional[TaskComplete] = None
    ) -> Task:
        """完成任务。★ 决策 5：自动 upsert checkin source='auto'。"""
        task = await self.get(task_id)
        if not task:
            raise NotFoundError(f"task {task_id} not found")
        if task.status == "done":
            return task

        task.status = "done"
        task.completed_at = datetime.now(timezone.utc)
        if payload and payload.actual_minutes is not None:
            task.actual_minutes = payload.actual_minutes

        # ★ 决策 5：今天自动打卡
        today = task.completed_at.date()
        await self.checkin_service.get_or_create_for_date(today, source="auto")

        await self.db.flush()
        # 显式 refresh，避免后续 Pydantic 序列化时触发 async lazy load
        await self.db.refresh(task)
        return task

    async def uncomplete(self, task_id: int) -> Task:
        """取消完成。注意：不删 checkin（用户可能单独打卡了）。

        但要更新 task 状态。
        """
        task = await self.get(task_id)
        if not task:
            raise NotFoundError(f"task {task_id} not found")
        if task.status != "done":
            return task

        task.status = "pending"
        task.completed_at = None
        task.actual_minutes = None
        await self.db.flush()
        return task

    async def reschedule(self, task_id: int, payload: TaskReschedule) -> Task:
        """改期。★ 决策 3：
            - planned_date = new_date
            - original_date 不变
            - shift_count += 1
        """
        task = await self.get(task_id)
        if not task:
            raise NotFoundError(f"task {task_id} not found")

        task.planned_date = payload.new_date
        task.shift_count += 1
        await self.db.flush()
        return task

    async def batch_update(self, payload: TaskBatchUpdate) -> TaskBatchResult:
        """批量更新。仅支持非日期字段的批量更新（改期请走 /reschedule）。"""
        if not payload.task_ids:
            return TaskBatchResult(updated=0, failed=[])

        # 不能批量改 planned_date（要走 /reschedule，每条加 shift_count）
        if payload.planned_date is not None:
            raise ValidationError(
                "批量改期请逐条走 /tasks/{id}/reschedule",
                details={"reason": "需要每条 task 单独 +shift_count"},
            )

        stmt = select(Task).where(Task.id.in_(payload.task_ids))
        tasks = list((await self.db.execute(stmt)).scalars())
        found_ids = {t.id for t in tasks}
        failed = [tid for tid in payload.task_ids if tid not in found_ids]

        update_fields = payload.model_dump(exclude_unset=True, exclude={"task_ids"})
        for task in tasks:
            for field, val in update_fields.items():
                setattr(task, field, val)
        await self.db.flush()
        return TaskBatchResult(updated=len(tasks), failed=failed)

    async def list_by_plan(
        self, plan_id: int, *, status: Optional[str] = None
    ) -> list[Task]:
        stmt = select(Task).where(Task.plan_id == plan_id)
        if status:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.planned_date, Task.priority.desc())
        return list((await self.db.execute(stmt)).scalars())

    async def list_by_date(
        self, d: date, *, plan_id: Optional[int] = None
    ) -> list[Task]:
        """按 planned_date 查今日任务（日历显示用 planned_date，决策 3）。"""
        stmt = select(Task).where(Task.planned_date == d)
        if plan_id:
            stmt = stmt.where(Task.plan_id == plan_id)
        stmt = stmt.order_by(Task.priority.desc())
        return list((await self.db.execute(stmt)).scalars())

    async def list_range(
        self, start: date, end: date, *, plan_id: Optional[int] = None
    ) -> list[Task]:
        stmt = select(Task).where(Task.planned_date >= start, Task.planned_date <= end)
        if plan_id:
            stmt = stmt.where(Task.plan_id == plan_id)
        stmt = stmt.order_by(Task.planned_date, Task.priority.desc())
        return list((await self.db.execute(stmt)).scalars())

    async def delete(self, task_id: int) -> bool:
        task = await self.get(task_id)
        if not task:
            return False
        await self.db.delete(task)
        await self.db.flush()
        return True
