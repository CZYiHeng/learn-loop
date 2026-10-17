"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.plans import router as plans_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.checkins import router as checkins_router
from app.api.v1.stats import router as stats_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(plans_router)
api_router.include_router(tasks_router)
api_router.include_router(checkins_router)
api_router.include_router(stats_router)

# M3+ 在此追加：
# api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
# api_router.include_router(review_router, prefix="/review-cards", tags=["review"])
# api_router.include_router(resources_router, prefix="/resources", tags=["resources"])
# api_router.include_router(qa_router, prefix="/qa", tags=["qa"])
# api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
