"""prompts 包 — LLM 提示词模板。M3 只做 plan，后续加 qa/cards/expand。"""
from app.ai.prompts.plan import (
    PLAN_SYSTEM_PROMPT,
    PLAN_TOOL_SCHEMA,
    PLAN_REPAIR_PROMPT,
    SKELETON_FALLBACK,
    build_plan_user_prompt,
)

__all__ = [
    "PLAN_SYSTEM_PROMPT",
    "PLAN_TOOL_SCHEMA",
    "PLAN_REPAIR_PROMPT",
    "SKELETON_FALLBACK",
    "build_plan_user_prompt",
]
