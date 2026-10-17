"""日志 — 结构化输出，按 env 切换级别。

不引 loguru/logstruct：logging 够用。开发期看到 DEBUG，生产 WARN+。
"""

from __future__ import annotations

import logging
import sys

from app.core.config import settings

# 一次性配置
_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str = "studyhub") -> logging.Logger:
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level.upper())
    logger.propagate = False  # 避免 root logger 重复输出

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = (
            "%(asctime)s [%(levelname)s] %(name)s "
            "%(message)s"
        )
        handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)

    _loggers[name] = logger
    return logger
