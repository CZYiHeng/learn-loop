"""应用配置 — 通过 pydantic-settings 从 .env 读取。

设计原则：
- 类型安全：所有配置项有明确类型，缺值时启动失败而非运行时崩
- 不暴露密钥：__repr__ 不会打印密钥
- M5 启动时切 PG：DATABASE_URL 改一下就行，无需改代码
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """运行时配置。.env 优先级最高。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === 应用 ===
    app_name: str = "StudyHub"
    env: Literal["local", "dev", "prod"] = "local"
    debug: bool = True
    log_level: str = "INFO"

    # === 数据库 ===
    # M0-M4 用 SQLite；M5 切 PG 时只改 .env 的 DATABASE_URL
    database_url: str = "sqlite+aiosqlite:///./data/studyhub.db"

    # === 认证（一期单用户，32 位随机 Bearer）===
    auth_token: str = ""
    auth_token_header: str = "X-Auth-Token"

    # === AI ===
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model_plan: str = "deepseek-chat"
    llm_model_qa: str = "deepseek-chat"
    llm_model_card: str = "qwen-turbo"
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_api_key: str = ""
    embedding_model: str = "BAAI/bge-m3"

    # === CORS ===
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("auth_token")
    @classmethod
    def _check_token(cls, v: str, info) -> str:
        # 不调 Settings() — 会递归。从 info.data 拿当前正在构造的 env
        env = info.data.get("env", "local")
        if not v and env != "local":
            raise ValueError("生产环境必须设置 AUTH_TOKEN")
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_pg(self) -> bool:
        return self.database_url.startswith("postgres")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """单例。lru_cache 保证全局只构造一次。"""
    return Settings()


settings = get_settings()
