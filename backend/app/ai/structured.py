"""Structured plan generation — 三级降级解析 + 业务校验 + repair。

★ 决策 12：三级降级
  1. function calling (tool_choice='required')
  2. response_format: json_object
  3. prompt 约束 + 正则抠 JSON + 容错解析

★ 5 条业务校验：
  ① 每天都有任务无空洞
  ② 总量 ≤ weekly_hours×7×weeks×1.3
  ③ 每日任务 1-8 条、单条 15-180 分钟
  ④ 阶段 3-12 个
  ⑤ 每周至少 1 条含「复习」的任务

★ repair：失败回灌具体错误（"day 2026-11-05 没有任务"）最多 2 次
★ 骨架兜底：仍失败返 SKELETON_FALLBACK
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from app.ai.client import LLMClient, LLMError, get_llm_client
from app.ai.prompts.plan import (
    PLAN_SYSTEM_PROMPT,
    PLAN_TOOL_SCHEMA,
    PLAN_REPAIR_PROMPT,
    SKELETON_FALLBACK,
    build_plan_user_prompt,
)

logger = logging.getLogger("studyhub.ai.structured")


# === 内部 Pydantic 校验模型（确保 LLM 返回符合结构） ===

class StageSpec(BaseModel):
    title: str
    order: int
    summary: Optional[str] = None


class TaskSpec(BaseModel):
    title: str
    stage_order: int
    planned_date: date
    estimated_minutes: int
    description: Optional[str] = None
    priority: int = 3


class PlanSpec(BaseModel):
    title: str
    stages: list[StageSpec]
    tasks: list[TaskSpec]


# === 输出 ===

@dataclass
class PlanGenerationResult:
    """一次生成的结果。无论成功失败都有，由上层判断走哪条路。"""
    plan: dict[str, Any]  # 符合 PlanSpec 结构的 dict
    strategy: str  # 'function_call' / 'json_object' / 'regex' / 'skeleton'
    repair_attempts: int = 0
    token_usage: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)  # 校验失败的具体错误


class PlanGenerationError(Exception):
    """三次降级都失败，最终走骨架兜底。"""


# === 主入口 ===

async def generate_structured_plan(
    goal: str,
    scenario: str,
    weeks: int,
    weekly_hours: int,
    start_date: date,
    end_date: date,
    *,
    client: Optional[LLMClient] = None,
) -> PlanGenerationResult:
    """生成结构化学习计划。

    返回 PlanGenerationResult，绝不上抛异常（保证 service 层能拿到结果）。
    """
    client = client or get_llm_client()

    user_prompt = build_plan_user_prompt(
        goal=goal,
        scenario=scenario,
        weeks=weeks,
        weekly_hours=weekly_hours,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    messages = [
        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    total_tokens: dict[str, int] = {}
    errors_history: list[str] = []

    # ★ 降级 1：function calling
    result = await _try_function_call(client, messages, total_tokens)
    if result is not None:
        # 校验
        plan, errs = _validate_plan(result, start_date, end_date, weeks, weekly_hours)
        if not errs:
            return PlanGenerationResult(
                plan=plan, strategy="function_call", repair_attempts=0,
                token_usage=total_tokens,
            )
        errors_history.extend(errs)

        # ★ repair 1：回灌具体错误重试
        plan2, errs2, tokens2 = await _repair_attempt(
            client, messages, errs, total_tokens, mode="function_call"
        )
        if plan2 and not errs2:
            return PlanGenerationResult(
                plan=plan2, strategy="function_call", repair_attempts=1,
                token_usage=tokens2,
            )
        errors_history.extend(errs2)

        # ★ repair 2：第二次重试
        plan3, errs3, tokens3 = await _repair_attempt(
            client, messages, errs2 or errs, tokens2, mode="function_call"
        )
        if plan3 and not errs3:
            return PlanGenerationResult(
                plan=plan3, strategy="function_call", repair_attempts=2,
                token_usage=tokens3,
            )
        errors_history.extend(errs3)

    # ★ 降级 2：response_format: json_object
    result_json = await _try_json_object(client, messages, total_tokens)
    if result_json is not None:
        plan, errs = _validate_plan(result_json, start_date, end_date, weeks, weekly_hours)
        if not errs:
            return PlanGenerationResult(
                plan=plan, strategy="json_object", repair_attempts=0,
                token_usage=total_tokens,
            )
        errors_history.extend(errs)

    # ★ 降级 3：prompt 约束 + 正则抠 JSON
    result_regex = await _try_regex_json(client, messages, total_tokens)
    if result_regex is not None:
        plan, errs = _validate_plan(result_regex, start_date, end_date, weeks, weekly_hours)
        if not errs:
            return PlanGenerationResult(
                plan=plan, strategy="regex", repair_attempts=0,
                token_usage=total_tokens,
            )
        errors_history.extend(errs)

    # ★ 骨架兜底
    logger.warning("all 3 strategies failed, fallback to skeleton")
    return PlanGenerationResult(
        plan=SKELETON_FALLBACK,
        strategy="skeleton",
        repair_attempts=2,
        token_usage=total_tokens,
        errors=errors_history,
    )


# === 降级实现 ===

async def _try_function_call(
    client: LLMClient, messages: list[dict], tokens_acc: dict
) -> Optional[dict]:
    """降级 1：function calling。"""
    try:
        resp = await client.complete(
            messages,
            tools=[PLAN_TOOL_SCHEMA],
            tool_choice="required",  # 强制调用
            temperature=0.7,
            max_tokens=8192,
        )
        _merge_tokens(tokens_acc, resp.get("token_usage", {}))
        if not resp.get("tool_calls"):
            return None
        args_str = resp["tool_calls"][0]["function"]["arguments"]
        return _safe_json_parse(args_str)
    except (LLMError, Exception) as e:
        logger.warning("function_call failed: %s", e)
        return None


async def _try_json_object(
    client: LLMClient, messages: list[dict], tokens_acc: dict
) -> Optional[dict]:
    """降级 2：response_format: json_object。"""
    # 重写 system prompt 让模型直接返 JSON
    messages2 = messages.copy()
    messages2[0] = {
        "role": "system",
        "content": PLAN_SYSTEM_PROMPT + "\n\n直接输出 JSON，不要调用工具。结构：{\"title\": ..., \"stages\": [...], \"tasks\": [...]}",
    }
    try:
        resp = await client.complete(
            messages2,
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=8192,
        )
        _merge_tokens(tokens_acc, resp.get("token_usage", {}))
        return _safe_json_parse(resp.get("content", ""))
    except (LLMError, Exception) as e:
        logger.warning("json_object failed: %s", e)
        return None


async def _try_regex_json(
    client: LLMClient, messages: list[dict], tokens_acc: dict
) -> Optional[dict]:
    """降级 3：prompt 约束 + 正则抠 JSON。"""
    messages2 = messages.copy()
    messages2[0] = {
        "role": "system",
        "content": PLAN_SYSTEM_PROMPT + "\n\n请只输出一段 JSON，包含在 ```json ... ``` 代码块中。结构同上。",
    }
    try:
        resp = await client.complete(messages2, temperature=0.7, max_tokens=8192)
        _merge_tokens(tokens_acc, resp.get("token_usage", {}))
        content = resp.get("content", "")
        return _extract_json_from_text(content)
    except (LLMError, Exception) as e:
        logger.warning("regex_json failed: %s", e)
        return None


async def _repair_attempt(
    client: LLMClient,
    original_messages: list[dict],
    errors: list[str],
    tokens_acc: dict,
    *,
    mode: str = "function_call",
) -> tuple[Optional[dict], list[str], dict]:
    """repair 重试。回灌具体错误，让模型修复。"""
    repair_msg = PLAN_REPAIR_PROMPT.format(errors="\n".join(f"- {e}" for e in errors))
    messages = original_messages + [
        # 注意：original_messages 没有上次的实际输出，repair 通过把错误描述给模型让它重新生成
        {"role": "user", "content": repair_msg},
    ]
    try:
        if mode == "function_call":
            resp = await client.complete(
                messages,
                tools=[PLAN_TOOL_SCHEMA],
                tool_choice="required",
                temperature=0.5,  # repair 时降温度
                max_tokens=8192,
            )
            _merge_tokens(tokens_acc, resp.get("token_usage", {}))
            if not resp.get("tool_calls"):
                return None, errors, tokens_acc
            args_str = resp["tool_calls"][0]["function"]["arguments"]
            plan = _safe_json_parse(args_str)
        else:
            resp = await client.complete(
                messages,
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=8192,
            )
            _merge_tokens(tokens_acc, resp.get("token_usage", {}))
            plan = _safe_json_parse(resp.get("content", ""))

        if plan is None:
            return None, ["repair 返回无效 JSON"], tokens_acc

        # 校验修复后的结果
        _, new_errs = _validate_plan(plan, date.today(), date.today() + timedelta(days=28), 4, 8)
        return plan, new_errs, tokens_acc
    except Exception as e:
        logger.warning("repair failed: %s", e)
        return None, [f"repair exception: {e}"], tokens_acc


# === JSON 解析工具 ===

def _safe_json_parse(s: str) -> Optional[dict]:
    """容错 JSON 解析。"""
    if not s:
        return None
    s = s.strip()
    # 直接试
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # 去掉 markdown 代码块
    m = re.search(r"```(?:json)?\s*(.+?)```", s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # 找第一个 { 到最后一个 }
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(s[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _extract_json_from_text(text: str) -> Optional[dict]:
    """从自由文本中抠出 JSON。"""
    return _safe_json_parse(text)


def _merge_tokens(acc: dict, new: dict) -> None:
    """累加 token 用量。"""
    for k, v in new.items():
        acc[k] = acc.get(k, 0) + (v or 0)


# === 5 条业务校验 ===

def _validate_plan(
    plan: dict,
    start_date: date,
    end_date: date,
    weeks: int,
    weekly_hours: int,
) -> tuple[dict, list[str]]:
    """校验 plan 是否符合 5 条规则。返回 (plan, errors)。

    校验失败时 plan 不修改，errors 列出具体问题。
    """
    errors: list[str] = []

    # 先用 Pydantic 校验结构
    try:
        spec = PlanSpec.model_validate(plan)
    except ValidationError as e:
        # 结构问题，返回骨架
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            errors.append(f"字段 {loc}: {err['msg']}")
        return plan, errors

    # ★ 业务校验 5 条
    # ① 每天都有任务无空洞（按 planned_date 检查）
    tasks_by_date: dict[str, list] = {}
    for t in spec.tasks:
        tasks_by_date.setdefault(t.planned_date.isoformat(), []).append(t)

    # 计算应该有的日期范围
    expected_dates: set[str] = set()
    cur = start_date
    while cur <= end_date:
        expected_dates.add(cur.isoformat())
        cur += timedelta(days=1)

    missing = expected_dates - set(tasks_by_date.keys())
    if missing:
        # 排序后只报前 5 个，避免错误信息过长
        sorted_missing = sorted(missing)[:5]
        errors.append(f"以下日期没有任务：{', '.join(sorted_missing)}（共 {len(missing)} 天）")

    # ② 总量 ≤ weekly_hours×7×weeks×1.3
    total_minutes = sum(t.estimated_minutes for t in spec.tasks)
    max_minutes = weekly_hours * 60 * 7 * weeks * 1.3
    if total_minutes > max_minutes:
        errors.append(
            f"总任务量 {total_minutes} 分钟超过上限 {int(max_minutes)} 分钟"
            f"（每周 {weekly_hours}h × 7 × {weeks} 周 × 1.3）"
        )

    # ③ 每日任务 1-8 条、单条 15-180 分钟
    for d, ts in tasks_by_date.items():
        if len(ts) > 8:
            errors.append(f"日期 {d} 有 {len(ts)} 条任务（上限 8 条）")
        for t in ts:
            if t.estimated_minutes < 5 or t.estimated_minutes > 600:
                errors.append(
                    f"任务「{t.title}」时长 {t.estimated_minutes} 分钟超出范围 5-600"
                )

    # ④ 阶段 3-12 个
    n_stages = len(spec.stages)
    if n_stages < 3 or n_stages > 12:
        errors.append(f"阶段数 {n_stages} 不在范围 3-12")

    # ⑤ 每周至少 1 条含「复习」的任务
    # 按周分组检查
    weeks_with_review: set[int] = set()
    for t in spec.tasks:
        if "复习" in t.title:
            # 算它属于第几周
            days_since_start = (t.planned_date - start_date).days
            week_idx = days_since_start // 7 + 1
            weeks_with_review.add(week_idx)

    expected_weeks = set(range(1, weeks + 1))
    missing_review_weeks = expected_weeks - weeks_with_review
    if missing_review_weeks:
        errors.append(
            f"第 {','.join(str(w) for w in sorted(missing_review_weeks))} 周没有含「复习」的任务"
        )

    return plan, errors
