"""API v1 路由聚合。M0 仅 health；M1+ 会逐步加 plans/tasks/checkins/..."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)

# M1+ 在此追加：
# api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
# api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
# ...
