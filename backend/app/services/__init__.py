"""services 包 — 业务逻辑层。

设计：路由只做参数校验 + 调 service + 返回；service 持有事务和业务规则。
"""
from app.services.checkin_service import CheckinService
from app.services.task_service import TaskService
from app.services.plan_service import PlanService
from app.services.stats_service import StatsService

__all__ = ["CheckinService", "TaskService", "PlanService", "StatsService"]
