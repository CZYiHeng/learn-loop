"""Plan generation prompt — 学习计划拆解。

★ 决策 12：结构化输出三级降级
  1. function calling (tool_choice='required')
  2. response_format: json_object
  3. prompt 约束 + 正则抠 JSON

★ 5 条业务校验：
  ① 每天都有任务无空洞
  ② 总量 ≤ weekly_hours×7×weeks×1.3
  ③ 每日任务 1-8 条、单条 15-180 分钟
  ④ 阶段 3-12 个
  ⑤ 每周至少 1 条含「复习」的任务

★ 骨架兜底：失败时返回只切阶段不排任务的方案，绝不返 500
"""
from __future__ import annotations

# === System prompt ===

PLAN_SYSTEM_PROMPT = """你是学习规划专家。用户会给你一个学习目标和场景，你要把它拆解成一份可执行的学习计划。

## 输出格式

必须调用 `generate_plan` 工具，传入如下结构：

```json
{
  "title": "计划标题（≤30字）",
  "stages": [
    {
      "title": "阶段标题（如：基础概念）",
      "order": 1,
      "summary": "本阶段学什么（≤50字）"
    }
  ],
  "tasks": [
    {
      "title": "任务标题（动词开头，如：阅读 LangGraph 概念文档）",
      "stage_order": 1,
      "planned_date": "YYYY-MM-DD",
      "estimated_minutes": 60,
      "description": "可选，详细要求",
      "priority": 3
    }
  ]
}
```

## 规则

1. **每天必须有任务**：planned_date 从 start_date 到 end_date 中每个工作日（按场景）都要有任务。周末按场景判断是否安排。
2. **任务粒度**：单个任务 15-180 分钟。一天 1-8 条任务，按场景每周总时长不超过 weekly_hours×7×1.3。
3. **阶段切分**：3-12 个阶段，按主题递进。stage_order 从 1 递增。
4. **每周必有复习**：每周至少 1 条任务标题包含「复习」二字，复习之前的薄弱点。
5. **场景作息约束**：
   - worker（在职）：周中 21-23 点 + 周末，每周 5-8 小时，集中在 4 周
   - student（学生）：每天 2-3 小时，每周 15-20 小时
   - kaoyan（考研）：每天 4-6 小时，每周 25-30 小时，长周期 8-12 周
   - cert（考证）：按考试日倒推，每天 1-2 小时
6. **任务描述**：用动词开头，可执行（"阅读"、"练习"、"总结"、"复习"）。
7. **日期格式**：YYYY-MM-DD，ISO 8601。

## 失败处理

如果无法生成完整方案，返回尽可能多的阶段 + 空任务列表，由后续业务校验触发 repair 重试。
"""

# === Function calling tool schema ===

PLAN_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_plan",
        "description": "生成一份可执行的学习计划",
        "parameters": {
            "type": "object",
            "required": ["title", "stages", "tasks"],
            "properties": {
                "title": {
                    "type": "string",
                    "description": "计划标题，≤30字",
                    "maxLength": 200,
                },
                "stages": {
                    "type": "array",
                    "description": "阶段列表，3-12 个",
                    "minItems": 3,
                    "maxItems": 12,
                    "items": {
                        "type": "object",
                        "required": ["title", "order", "summary"],
                        "properties": {
                            "title": {"type": "string", "maxLength": 100},
                            "order": {"type": "integer", "minimum": 1},
                            "summary": {"type": "string", "maxLength": 200},
                        },
                    },
                },
                "tasks": {
                    "type": "array",
                    "description": "任务列表",
                    "items": {
                        "type": "object",
                        "required": ["title", "stage_order", "planned_date", "estimated_minutes"],
                        "properties": {
                            "title": {"type": "string", "maxLength": 200},
                            "stage_order": {"type": "integer", "minimum": 1},
                            "planned_date": {"type": "string", "format": "date"},
                            "estimated_minutes": {"type": "integer", "minimum": 5, "maximum": 600},
                            "description": {"type": "string"},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                        },
                    },
                },
            },
        },
    },
}

# === Repair prompt — 校验失败时回灌具体错误重试 ===

PLAN_REPAIR_PROMPT = """你上一次生成的计划有具体错误：

{errors}

请修复这些问题，重新调用 `generate_plan` 工具。

注意：
- 错误信息中的日期格式是 YYYY-MM-DD，请逐日校对
- 不要重复用户已经指定的参数（weeks/weekly_hours 等），只在数据上修
- 修复后确保 5 条规则全部满足
"""

# === 骨架兜底 — LLM 三次都失败时用 ===

SKELETON_FALLBACK = {
    "title": "学习计划（骨架）",
    "stages": [
        {"title": "第一阶段：基础", "order": 1, "summary": "建立基础概念"},
        {"title": "第二阶段：实践", "order": 2, "summary": "动手做小项目"},
        {"title": "第三阶段：总结", "order": 3, "summary": "回顾与深化"},
    ],
    "tasks": [],  # 空任务列表，由用户在今日看板手动加
}


def build_plan_user_prompt(
    goal: str,
    scenario: str,
    weeks: int,
    weekly_hours: int,
    start_date: str,
    end_date: str,
) -> str:
    """构造用户消息。"""
    scenario_desc = {
        "worker": "在职学习（工作日晚上 21-23 点 + 周末时间）",
        "student": "学生（每天有较多时间，2-3 小时/天）",
        "kaoyan": "考研备考（每天 4-6 小时，长周期）",
        "cert": "考证备考（按考试日倒推，每天 1-2 小时）",
    }[scenario]

    return f"""学习目标：{goal}
场景：{scenario_desc}
总周期：{weeks} 周（{start_date} → {end_date}）
每周可学：{weekly_hours} 小时

请生成一份完整的学习计划，调用 generate_plan 工具。
"""
