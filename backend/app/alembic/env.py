"""Alembic 迁移环境。

设计：从 app.core.config 读 settings.database_url，避免双重配置。
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings

# 触发全部模型注册到 metadata
from app import models  # noqa: F401
from app.models.base import Base

config = context.config

# 把 sync URL 推给 alembic（async URL 不能直接给 alembic offline）
sync_url = settings.database_url.replace(
    "sqlite+aiosqlite", "sqlite"
).replace(
    "postgresql+asyncpg", "postgresql+psycopg2"
)
config.set_main_option("sqlalchemy.url", sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """offline 模式：生成 SQL 不连接数据库。"""
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """online 模式：连接数据库执行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite 不支持 ALTER，需要 batch mode
            render_as_batch=settings.is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
