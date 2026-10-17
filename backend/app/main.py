"""应用入口 — create_app + lifespan + 路由挂载 + 中间件注册。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.db import engine_lifespan
from app.core.errors import register_error_handlers
from app.core.logging import get_logger
from app.core.middleware import RequestIdMiddleware

logger = get_logger("studyhub.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：启动时初始化数据库，退出时清理。"""
    logger.info("app starting", extra={"env": settings.env, "app": settings.app_name})
    async with engine_lifespan():
        # 触发所有模型注册（确保 metadata 完整）
        from app import models  # noqa: F401
        logger.info("db ready")
        yield
    logger.info("app stopping")


def create_app() -> FastAPI:
    """构造 FastAPI 应用实例。"""
    app = FastAPI(
        title=settings.app_name,
        version=__import__("app").__version__,
        description="个人学习计划系统 — 每天告诉你该干什么",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # 中间件
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    # 路由
    # /health 系统级探活，挂根路径
    app.include_router(api_router, prefix="/api/v1")
    # 同时提供 /health 别名（部署探活用）
    from app.api.v1.health import router as health_router
    app.include_router(health_router, tags=["health"])

    # 错误处理
    register_error_handlers(app)

    return app


app = create_app()
