"""模型包导出 — 导入本文件即触发全部模型注册到 metadata。

注册顺序：base → plan → checkin（含 task） → review → resource → ai → setting
"""

from app.models.base import Base, TimestampMixin
from app.models.plan import StudyPlan
from app.models.checkin import Task, Checkin
from app.models.review import ReviewCard, ReviewLog, SM2_ALGORITHM_VERSION, QUALITY_MAP
from app.models.resource import Resource, ResourceChunk, FileObject
from app.models.ai import AIGeneration, QAConversation, QAMessage
from app.models.setting import Setting

__all__ = [
    "Base", "TimestampMixin",
    "StudyPlan",
    "Task", "Checkin",
    "ReviewCard", "ReviewLog", "SM2_ALGORITHM_VERSION", "QUALITY_MAP",
    "Resource", "ResourceChunk", "FileObject",
    "AIGeneration", "QAConversation", "QAMessage",
    "Setting",
]
