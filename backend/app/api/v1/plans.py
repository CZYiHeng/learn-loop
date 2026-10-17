"""Plans 路由 — 学习计划 CRUD + 进度 + AI 生成。"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.pagination import page_params, PageParams
from app.deps import get_db, get_current_user
from app.schemas.common import PageResponse
from app.schemas.plan import (
    StudyPlanCreate, StudyPlanUpdate, StudyPlanOut, PlanProgress,
)
from app.services.plan_service import PlanService
from app.services.ai_plan_service import AIPlanService

router = APIRouter(prefix="/plans", tags=["plans"])


# === AI 生成 — M3 入口流程 ===

class PlanGenerateRequest(BaseModel):
    """★ 修订计划 electric-pulse：goal + scenario，其余反推。"""
    goal: str = Field(..., min_length=1, max_length=500)
    scenario: Literal["student", "worker", "kaoyan", "cert"] = "worker"
    # 以下可由 scenario 反推，前端默认不传
    weeks: int | None = None
    weekly_hours: int | None = None
    start_date: date | None = None
    end_date: date | None = None


class PlanGenerateResponse(BaseModel):
    generation_id: int
    plan_id: int | None = None  # 同步生成：直接给 plan_id；前端无需轮询
    status: str


def _scenario_defaults(scenario: str) -> tuple[int, int]:
    """场景反推作息约束。"""
    return {
        "worker": (4, 6),
        "student": (8, 18),
        "kaoyan": (12, 28),
        "cert": (8, 10),
    }.get(scenario, (4, 6))


@router.post("/generate", response_model=PlanGenerateResponse, status_code=status.HTTP_201_CREATED, summary="AI 生成学习计划")
async def generate_plan(
    payload: PlanGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    """★ 修订 electric-pulse：goal + scenario → 同步生成 → 直接进今日看板。

    M0 用同步等待（单人，无所谓），生产可改 202 + 轮询。
    """
    # 场景反推参数
    weeks = payload.weeks
    weekly_hours = payload.weekly_hours
    if weeks is None or weekly_hours is None:
        w, wh = _scenario_defaults(payload.scenario)
        weeks = weeks or w
        weekly_hours = weekly_hours or wh

    start_date = payload.start_date or date.today()
    end_date = payload.end_date or (start_date + timedelta(weeks=weeks))

    svc = AIPlanService(db)
    plan_id, result = await svc.generate(
        goal=payload.goal,
        scenario=payload.scenario,
        weeks=weeks,
        weekly_hours=weekly_hours,
        start_date=start_date,
        end_date=end_date,
    )
    # 拿 generation_id
    from app.models.ai import AIGeneration
    from sqlalchemy import select
    gen_stmt = select(AIGeneration).where(AIGeneration.plan_id == plan_id).order_by(AIGeneration.id.desc()).limit(1)
    gen = (await db.execute(gen_stmt)).scalar_one_or_none()
    return PlanGenerateResponse(
        generation_id=gen.id if gen else 0,
        plan_id=plan_id,
        status="succeeded",
    )


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
