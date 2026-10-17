# StudyHub · 学习看板

> 不是「学习管理后台」，是「每天告诉你该干什么」的系统。

## 状态

- **M0 地基**：进行中
- **数据库**：SQLite（M0-M4 本地）；M5 RAG 启动时切 PostgreSQL 16 + pgvector
- **部署**：M6 启动时上国内轻量服务器 + 备案

## 目录

```
backend/    FastAPI + SQLAlchemy 2.0 + Alembic
frontend/   Vue 3 + Vite + TS + Pinia + Naive UI
deploy/     Nginx / systemd / 备份脚本
docs/       API 文档、Schema 说明、部署 Runbook
```

## 启动

详见 `docs/deploy-runbook.md`。本地开发最快：

```bash
cd backend
uv venv --python 3.12 .venv
.venv/Scripts/activate          # Windows
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## 计划

详见 `C:\Users\admin\.workbuddy\plans\radiant-thunder-einstein-CkTFmyE6.md`
