"""AI plan generation service — 幂等 + 事务落库 + 审计。

★ 决策 12（关键）：
- request_hash = sha256(goal + scenario + weeks + weekly_hours + start_date + prompt_version)
  ← 不含 client_request_id
- LLM 调用在事务外，绝不把网络调用放进 DB 事务
- 单事务落库 plan + tasks，异常整体回滚
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.structured import generate_structured_plan, PlanGenerationResult
from app.models.ai import AIGeneration
from app.models.plan import StudyPlan
from app.models.checkin import Task
from app.schemas.plan import StudyPlanCreate

logger = logging.getLogger("studyhub.ai.plan_service")

PROMPT_VERSION = "plan-v2"  # v2: 加「按目标元素拆分」规则，修复泛化问题


class AIPlanService:
    """AI 计划生成服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def compute_request_hash(
        self,
        goal: str,
        scenario: str,
        weeks: int,
        weekly_hours: int,
        start_date: date,
    ) -> str:
        """★ 不含 client_request_id，保证幂等。

        同样输入下 hash 一致，第二次生成会直接命中已有 plan。
        """
        raw = f"{goal}|{scenario}|{weeks}|{weekly_hours}|{start_date.isoformat()}|{PROMPT_VERSION}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def find_existing_generation(self, request_hash: str) -> Optional[AIGeneration]:
        """幂等检查：命中 succeeded 直接返回已有 plan_id（0 次 LLM 调用）。"""
        stmt = select(AIGeneration).where(
            AIGeneration.request_hash == request_hash,
            AIGeneration.status == "succeeded",
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def acquire_execution(
        self, request_hash: str, payload: dict
    ) -> AIGeneration:
        """抢执行权 — INSERT status='pending'。"""
        gen = AIGeneration(
            task_type="plan",
            request_hash=request_hash,
            status="pending",
            request_payload={**payload, "prompt_version": PROMPT_VERSION},
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(gen)
        await self.db.flush()
        return gen

    async def generate(
        self,
        goal: str,
        scenario: str,
        weeks: int,
        weekly_hours: int,
        start_date: date,
        end_date: date,
        *,
        generation_id: Optional[int] = None,
    ) -> tuple[int, PlanGenerationResult]:
        """完整生成流程。返回 (plan_id, result)。

        LLM 调用在事务外，落库在单事务内（决策 12 关键）。
        """
        request_hash = self.compute_request_hash(
            goal, scenario, weeks, weekly_hours, start_date
        )

        # 1. 幂等检查
        existing = await self.find_existing_generation(request_hash)
        if existing and existing.plan_id:
            logger.info("hit idempotency cache, plan_id=%s", existing.plan_id)
            return existing.plan_id, PlanGenerationResult(
                plan={}, strategy="cache_hit", repair_attempts=0,
                token_usage=existing.token_usage or {},
            )

        # 2. 抢执行权（同时记录 generation）
        payload = {
            "goal": goal,
            "scenario": scenario,
            "weeks": weeks,
            "weekly_hours": weekly_hours,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        gen = await self.acquire_execution(request_hash, payload)

        # 3. 状态 → running
        gen.status = "running"
        await self.db.flush()

        # 4. ★ LLM 调用（在事务外） — 但 async session 不会真的开始事务直到 commit
        #    这里我们先把当前 session flush 出去（保证 pending 状态落库），再调 LLM
        await self.db.commit()  # 释放锁，让其他请求看到 pending 状态

        try:
            result = await generate_structured_plan(
                goal=goal,
                scenario=scenario,
                weeks=weeks,
                weekly_hours=weekly_hours,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            # LLM 异常，标记失败
            await self._mark_failed(gen, str(e), 0)
            raise

        # 5. ★ 单事务落库 plan + tasks（决策 12 关键）
        plan_id = await self._persist_plan(
            gen, result, goal, scenario, weeks, weekly_hours, start_date, end_date
        )

        return plan_id, result

    async def _persist_plan(
        self,
        gen: AIGeneration,
        result: PlanGenerationResult,
        goal: str,
        scenario: str,
        weeks: int,
        weekly_hours: int,
        start_date: date,
        end_date: date,
    ) -> int:
        """★ 单事务落库 plan + tasks。任何异常整体回滚。"""
        try:
            # 重新开启事务
            plan = StudyPlan(
                title=result.plan.get("title", "学习计划"),
                goal=goal,
                scenario=scenario,
                origin="ai",
                weeks=weeks,
                weekly_hours=weekly_hours,
                start_date=start_date,
                end_date=end_date,
                status="active",
            )
            self.db.add(plan)
            await self.db.flush()  # 拿到 plan.id

            # 批量插入 tasks
            tasks_data = result.plan.get("tasks", [])
            stages = result.plan.get("stages", [])
            stage_title_map = {s["order"]: s["title"] for s in stages}

            task_objs = []
            for t in tasks_data:
                planned_date_str = t.get("planned_date")
                try:
                    planned_date = date.fromisoformat(planned_date_str) if isinstance(planned_date_str, str) else planned_date_str
                except (ValueError, TypeError):
                    continue  # 跳过日期无效的 task

                stage_order = t.get("stage_order")
                task = Task(
                    plan_id=plan.id,
                    title=t.get("title", "未命名任务"),
                    description=t.get("description"),
                    original_date=planned_date,  # ★ 决策 3：初始一致
                    planned_date=planned_date,
                    stage_title=stage_title_map.get(stage_order, "未分组") if stage_order else "未分组",
                    stage_order=stage_order,
                    estimated_minutes=t.get("estimated_minutes", 60),
                    priority=t.get("priority", 3),
                    status="pending",
                    shift_count=0,
                )
                task_objs.append(task)

            if task_objs:
                self.db.add_all(task_objs)
                await self.db.flush()

            # 更新 generation 状态
            gen.status = "succeeded"
            gen.response_payload = result.plan
            gen.repair_attempts = result.repair_attempts
            gen.token_usage = result.token_usage
            gen.plan_id = plan.id
            gen.finished_at = datetime.now(timezone.utc)
            await self.db.flush()

            await self.db.commit()
            return plan.id

        except Exception as e:
            # 整体回滚 — 但 generation 也要标记失败
            await self.db.rollback()
            logger.error("persist plan failed, rolled back: %s", e)
            # 重新打开 session 记录失败
            gen.status = "failed"
            gen.error_message = f"persist failed: {e}"
            gen.finished_at = datetime.now(timezone.utc)
            self.db.add(gen)
            await self.db.commit()
            raise

    async def _mark_failed(self, gen: AIGeneration, error_msg: str, repair_attempts: int) -> None:
        gen.status = "failed"
        gen.error_message = error_msg
        gen.repair_attempts = repair_attempts
        gen.finished_at = datetime.now(timezone.utc)
        await self.db.commit()
