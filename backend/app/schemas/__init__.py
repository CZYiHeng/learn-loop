"""schemas 包 — Pydantic I/O 模型，与 SQLAlchemy model 严格分离。

设计原则：
- model 是 ORM 表结构，schemas 是 API 边界的契约
- 输入与输出模型分离：Create 不含 id/created_at；Out 含全部字段
- 一个 model 可对应多个 schema（如 TaskCreate vs TaskBatchUpdate）
"""
from app.schemas.common import PageResponse
from app.schemas.plan import (
    StudyPlanCreate, StudyPlanUpdate, StudyPlanOut, PlanProgress,
)
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskOut, TaskComplete, TaskReschedule,
    TaskBatchUpdate, TaskBatchResult,
)
from app.schemas.checkin import (
    CheckinCreate, CheckinUpdate, CheckinOut, Streak,
)
from app.schemas.stats import TodayStats

__all__ = [
    "PageResponse",
    "StudyPlanCreate", "StudyPlanUpdate", "StudyPlanOut", "PlanProgress",
    "TaskCreate", "TaskUpdate", "TaskOut", "TaskComplete", "TaskReschedule",
    "TaskBatchUpdate", "TaskBatchResult",
    "CheckinCreate", "CheckinUpdate", "CheckinOut", "Streak",
    "TodayStats",
]
