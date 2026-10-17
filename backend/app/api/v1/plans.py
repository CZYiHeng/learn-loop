"""Plans 路由 — 学习计划 CRUD + 进度。

M3 才接 /plans/generate（AI 生成）。M1 暂只做手工 CRUD。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import page_params, PageParams
from app.deps import get_db, get_current_user
from app.schemas.common import PageResponse
from app.schemas.plan import (
    StudyPlanCreate, StudyPlanUpdate, StudyPlanOut, PlanProgress,
)
from app.services.plan_service import PlanService

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=PageResponse[StudyPlanOut], summary="列表")
async def list_plans(
    status_filter: str | None = Query(None, alias="status"),
    page: PageParams = Depends(page_params),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = PlanService(db)
    result = await svc.list(page, status=status_filter)
    return PageResponse[StudyPlanOut](
        items=[StudyPlanOut.model_validate(p) for p in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        has_next=result["has_next"],
    )


@router.post("", response_model=StudyPlanOut, status_code=status.HTTP_201_CREATED, summary="手工创建")
async def create_plan(
    payload: StudyPlanCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = PlanService(db)
    plan = await svc.create(payload)
    await db.commit()
    return StudyPlanOut.model_validate(plan)


@router.get("/{plan_id}", response_model=StudyPlanOut, summary="详情")
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = PlanService(db)
    plan = await svc.get(plan_id)
    if not plan:
        from app.core.errors import NotFoundError
        raise NotFoundError(f"plan {plan_id} not found")
    return StudyPlanOut.model_validate(plan)


@router.patch("/{plan_id}", response_model=StudyPlanOut, summary="更新")
async def update_plan(
    plan_id: int,
    payload: StudyPlanUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = PlanService(db)
    plan = await svc.update(plan_id, payload)
    await db.commit()
    return StudyPlanOut.model_validate(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除")
async def delete_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = PlanService(db)
    await svc.delete(plan_id)
    await db.commit()


@router.get("/{plan_id}/progress", response_model=PlanProgress, summary="进度聚合")
async def get_progress(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = PlanService(db)
    return await svc.get_progress(plan_id)
