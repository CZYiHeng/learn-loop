"""认证 — 一期单用户 32 位随机 Bearer Token。

设计：
- 不引入 JWT/OAuth：自己用，没有多用户也没有过期需求
- Token 通过环境变量注入，不放数据库
- M6 切到微信小程序时只改本文件（计划第十一节第 3 点）

用法：
    POST /api/v1/xxx
    Headers: X-Auth-Token: <32位随机>
"""

from __future__ import annotations

import secrets

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.errors import AuthError

# 用 Bearer scheme 让 OpenAPI 文档自动带 token 输入框
_bearer_scheme = HTTPBearer(auto_error=False)


def generate_token() -> str:
    """生成 32 位随机 token。命令行：python -m app.core.security gen"""
    return secrets.token_hex(16)


async def verify_token(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    x_auth_token: str | None = Header(None, alias=settings.auth_token_header),
) -> str:
    """依赖：校验请求中的 token。本地 dev 模式允许跳过。"""
    if settings.env == "local" and not settings.auth_token:
        return "local-user"

    token: str | None = None
    if creds and creds.scheme.lower() == "bearer":
        token = creds.credentials
    elif x_auth_token:
        token = x_auth_token

    if not token:
        raise AuthError("缺少认证 token")
    if not secrets.compare_digest(token, settings.auth_token):
        raise AuthError("token 无效")
    return token


# 全局依赖注入点（main.py 引用）
auth_dependency = Depends(verify_token)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "gen":
        print(generate_token())
