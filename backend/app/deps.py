"""依赖注入 — FastAPI Depends 的统一入口。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db as _get_db
from app.core.security import verify_token

# 重新导出，避免调用方写长路径
get_db = _get_db
get_current_user = verify_token
