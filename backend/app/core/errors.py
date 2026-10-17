"""统一错误处理。

错误响应格式（计划第五节约定）：
    {"error": {"code": "...", "message": "...", "details": {...}, "request_id": "..."}}

每个业务异常类对应一个稳定的 code，前端按 code 分支处理。
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class AppError(Exception):
    """业务异常基类。子类设置 code + http_status。"""

    code: str = "app_error"
    http_status: int = status.HTTP_400_BAD_REQUEST
    default_message: str = "请求处理失败"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


# === 常见业务异常 ===

class NotFoundError(AppError):
    code = "not_found"
    http_status = status.HTTP_404_NOT_FOUND
    default_message = "资源不存在"


class ConflictError(AppError):
    code = "conflict"
    http_status = status.HTTP_409_CONFLICT
    default_message = "资源已存在或状态冲突"


class ValidationError(AppError):
    code = "validation_error"
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_message = "输入校验失败"


class AuthError(AppError):
    code = "unauthorized"
    http_status = status.HTTP_401_UNAUTHORIZED
    default_message = "未授权"


class RateLimitError(AppError):
    code = "rate_limit"
    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    default_message = "请求过于频繁"


# === 异常 → JSON 响应 ===

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=_build_error_payload(exc.code, exc.message, exc.details, request),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    # 唯一约束 / 外键冲突
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=_build_error_payload(
            "integrity_error",
            "数据完整性冲突（可能重复或外键不满足）",
            {"db_error": str(exc.orig) if exc.orig else str(exc)},
            request,
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_map = {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        422: "validation_error",
        429: "rate_limit",
    }
    code = code_map.get(exc.status_code, "http_error")
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_payload(code, str(exc.detail), {}, request),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未捕获异常的兜底。永远不要返回 stacktrace 给前端。"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_payload(
            "internal_error",
            "服务器内部错误",
            {"exception_type": type(exc).__name__},
            request,
        ),
    )


def _build_error_payload(
    code: str, message: str, details: dict[str, Any], request: Request
) -> dict[str, Any]:
    """组装统一错误体。"""
    request_id = getattr(request.state, "request_id", None) or "unknown"
    return {
        "error": {
            "code": code,
            "message": message,
            "details": jsonable_encoder(details),
            "request_id": request_id,
        }
    }


def register_error_handlers(app) -> None:
    """在 main.py 的 create_app 里调用一次。"""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
