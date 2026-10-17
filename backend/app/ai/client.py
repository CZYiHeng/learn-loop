"""LLM 客户端 — 走 OpenAI 兼容协议，切换厂商只改 base_url + model。

★ 决策 8：Embedding 走 API 不本地跑；M0-M4 不需要 embedding
★ LLM 调用统计 token 用量，供 ai_generation 审计
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger("studyhub.ai")


class LLMClient:
    """LLM 客户端封装 — 走 OpenAI 兼容 SDK。"""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = base_url or settings.llm_base_url
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model_plan
        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=2,  # ★ 决策：max_retries=2，避免雪崩
            timeout=120.0,
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
    ) -> dict[str, Any]:
        """同步完成调用。返回 {content, tool_calls, token_usage}。

        失败抛 LLMError，由上层 service 捕获走降级。
        """
        kwargs: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

        try:
            resp = await self._client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            raise LLMError(f"LLM call failed: {e}") from e

        choice = resp.choices[0]
        message = choice.message
        token_usage = {}
        if resp.usage:
            token_usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens,
            }

        return {
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in (message.tool_calls or [])
            ],
            "token_usage": token_usage,
            "finish_reason": choice.finish_reason,
        }

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """流式生成 — M5 RAG 问答用。

        yield 每个 chunk 的 content delta。
        """
        stream = await self._client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class LLMError(Exception):
    """LLM 调用失败的统一异常。"""


_client_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """单例 LLM 客户端。lru_cache 不行（client 有可变状态），手动单例。"""
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = LLMClient()
    return _client_singleton
