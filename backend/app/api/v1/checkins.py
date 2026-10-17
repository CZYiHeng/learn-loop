"""Checkins 路由 — 每日打卡 + streak。"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.deps import get_db, get_current_user
from app.schemas.checkin import CheckinCreate, CheckinUpdate, CheckinOut, Streak
from app.services.checkin_service import CheckinService

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.get("", response_model=list[CheckinOut], summary="日期范围列表")
async def list_checkins(
    start: date,
    end: date,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = CheckinService(db)
    items = await svc.list_range(start, end)
    return [CheckinOut.model_validate(c) for c in items]


@router.get("/streak", response_model=Streak, summary="连续天数（决策 6：今天没活动不归零）")
async def get_streak(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = CheckinService(db)
    return await svc.get_streak()


@router.post("", response_model=CheckinOut, status_code=status.HTTP_201_CREATED, summary="打卡（upsert）")
async def upsert_checkin(
    payload: CheckinCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = CheckinService(db)
    checkin = await svc.upsert(payload)
    await db.commit()
    return CheckinOut.model_validate(checkin)


@router.patch("/{date}", response_model=CheckinOut, summary="更新")
async def update_checkin(
    date: date,
    payload: CheckinUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = CheckinService(db)
    checkin = await svc.update(date, payload)
    if not checkin:
        raise NotFoundError(f"checkin {date} not found")
    await db.commit()
    return CheckinOut.model_validate(checkin)


@router.delete("/{date}", status_code=status.HTTP_204_NO_CONTENT, summary="删除")
async def delete_checkin(
    date: date,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    svc = CheckinService(db)
    await svc.delete(date)
    await db.commit()
