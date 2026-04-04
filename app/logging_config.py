# -*- coding: utf-8 -*-
"""
Logging Configuration - 日志配置模块
集中管理应用日志配置，包括控制台输出和文件输出
"""

import logging
import logging.config
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "gateway_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "gateway.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "default",
            "encoding": "utf-8",
        },
        "uvicorn_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "uvicorn.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "default",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "gateway_file"],
            "level": logging.INFO,
        },
        "uvicorn": {
            "handlers": ["console", "uvicorn_file"],
            "level": logging.INFO,
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console", "uvicorn_file"],
            "level": logging.INFO,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console", "uvicorn_file"],
            "level": logging.INFO,
            "propagate": False,
        },
    },
}


def setup_logging():
    """初始化日志配置"""
    logging.config.dictConfig(LOGGING_CONFIG)
