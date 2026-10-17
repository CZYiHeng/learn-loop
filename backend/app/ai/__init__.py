"""AI 模块 — LLM 客户端 + RAG + 计划生成。

M3 启动：先做计划生成（含降级解析 + 业务校验）。
M5 加 RAG（embedding + retrieval + qa）。
"""
from app.ai.client import LLMClient, get_llm_client
from app.ai.structured import (
    generate_structured_plan,
    PlanGenerationResult,
    PlanGenerationError,
)

__all__ = [
    "LLMClient", "get_llm_client",
    "generate_structured_plan",
    "PlanGenerationResult", "PlanGenerationError",
]
