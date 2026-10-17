"""请求 ID + 日志中间件。

每个请求分配一个 request_id，注入到 request.state 和响应头 X-Request-Id，
方便定位「崩了的那次请求」。
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger("studyhub.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """注入 request_id，记录访问日志。"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 优先复用客户端传来的 X-Request-Id，没有就生成
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id

        start = time.perf_counter()
        method, path = request.method, request.url.path

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request failed", extra={
                    "method": method, "path": path,
                    "elapsed_ms": round(elapsed_ms, 1),
                }
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-Id"] = request_id

        logger.info(
            "request %s %s %d %.1fms",
            method, path, response.status_code, round(elapsed_ms, 1),
            extra={"request_id": request_id},
        )
        return response
