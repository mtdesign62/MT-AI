from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from mt_ai.config import AppPaths

LOGGER_NAME = "mt_ai"


def get_logger(component: str | None = None) -> logging.Logger:
    name = LOGGER_NAME if not component else f"{LOGGER_NAME}.{component}"
    return logging.getLogger(name)


def configure_logging(paths: AppPaths | None = None, level: int = logging.INFO) -> Path:
    app_paths = (paths or AppPaths.default()).ensure()
    log_file = app_paths.logs / "mt-ai.log"
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    target = str(log_file.resolve())
    already_configured = any(
        isinstance(handler, RotatingFileHandler)
        and getattr(handler, "baseFilename", None) == target
        for handler in logger.handlers
    )
    if not already_configured:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=4,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
    return log_file


def install_exception_hook() -> None:
    previous = sys.excepthook

    def hook(exc_type, exc_value, traceback_obj) -> None:
        get_logger("crash").critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, traceback_obj),
        )
        previous(exc_type, exc_value, traceback_obj)

    sys.excepthook = hook
