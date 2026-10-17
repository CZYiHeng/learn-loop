"""Tasks 路由 — 每日任务核心 CRUD + complete/uncomplete/reschedule/batch。"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.deps import get_db, get_current_user
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskOut, TaskComplete, TaskReschedule,
    TaskBatchUpdate, TaskBatchResult,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _serialize(task) -> TaskOut:
    return TaskOut.model_validate(task)


@router.get("", response_model=list[TaskOut], summary="列表（按 planned_date / plan_id 过滤）")
async def list_tasks(
    plan_id: Optional[int] = Query(None),
    planned_date: Optional[date] = Query(None, description="按 planned_date 精确匹配（决策 3：日历用）"),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = TaskService(db)
    if planned_date:
        tasks = await svc.list_by_date(planned_date, plan_id=plan_id)
    else:
        if plan_id:
            tasks = await svc.list_by_plan(plan_id, status=status_filter)
        else:
            # 没指定就给空（避免一次拿全表）
            tasks = []
    return [_serialize(t) for t in tasks]


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED, summary="创建")
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = TaskService(db)
    task = await svc.create(payload)
    await db.commit()
    return _serialize(task)


@router.get("/{task_id}", response_model=TaskOut, summary="详情")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = TaskService(db)
    task = await svc.get(task_id)
    if not task:
        raise NotFoundError(f"task {task_id} not found")
    return _serialize(task)


@router.patch("/{task_id}", response_model=TaskOut, summary="更新（不能直接改 planned_date）")
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = TaskService(db)
    task = await svc.update(task_id, payload)
    await db.commit()
    return _serialize(task)


@router.post("/{task_id}/complete", response_model=TaskOut, summary="完成（自动打卡）")
async def complete_task(
    task_id: int,
    payload: TaskComplete | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    """★ 决策 5：完成 task 自动 upsert checkin source='auto'。"""
    svc = TaskService(db)
    task = await svc.complete(task_id, payload)
    await db.commit()
    return _serialize(task)


@router.post("/{task_id}/uncomplete", response_model=TaskOut, summary="取消完成")
async def uncomplete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = TaskService(db)
    task = await svc.uncomplete(task_id)
    await db.commit()
    return _serialize(task)


@router.post("/{task_id}/reschedule", response_model=TaskOut, summary="改期（shift_count+1）")
async def reschedule_task(
    task_id: int,
    payload: TaskReschedule,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    """★ 决策 3：planned_date 变，original_date 不变，shift_count+1。"""
    svc = TaskService(db)
    task = await svc.reschedule(task_id, payload)
    await db.commit()
    return _serialize(task)


@router.post(":batch", response_model=TaskBatchResult, summary="批量更新")
async def batch_update_tasks(
    payload: TaskBatchUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = TaskService(db)
    result = await svc.batch_update(payload)
    await db.commit()
    return result


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = TaskService(db)
    await svc.delete(task_id)
    await db.commit()
