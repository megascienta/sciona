"""Logging helpers for SCIONA modules."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Mapping, Optional

from . import constants as setup_config

_DEBUG_ENABLED = False


def get_logger(name: str) -> logging.Logger:
    if name.startswith("sciona."):
        return logging.getLogger(name)
    return logging.getLogger(f"sciona.{name}")


def configure_logging(
    level: str | int | None = None,
    module_levels: Mapping[str, str] | None = None,
    *,
    debug: bool = False,
    structured: bool = False,
    repo_root: Optional[Path] = None,
) -> None:
    """Initialize a basic stdout/stderr logger unless one is already configured."""
    global _DEBUG_ENABLED
    if level is None:
        level = os.getenv("SCIONA_LOG_LEVEL", "INFO")
    if debug:
        level = "DEBUG"
    _DEBUG_ENABLED = debug or str(level).upper() == "DEBUG"
    if isinstance(level, str):
        level = logging._nameToLevel.get(level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    sciona_logger = logging.getLogger("sciona")
    sciona_logger.setLevel(level)
    if module_levels:
        for module_name, module_level in module_levels.items():
            if not module_name:
                continue
            if isinstance(module_level, str):
                resolved_level = logging._nameToLevel.get(module_level.upper(), level)
            else:
                resolved_level = int(module_level)
            logger_name = (
                module_name
                if module_name.startswith("sciona.")
                else f"sciona.{module_name}"
            )
            logging.getLogger(logger_name).setLevel(resolved_level)
    formatter: logging.Formatter
    if structured:
        formatter = logging.Formatter(
            '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    if not sciona_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        sciona_logger.addHandler(handler)
    else:
        for handler in sciona_logger.handlers:
            handler.setFormatter(formatter)
    _maybe_add_file_handler(sciona_logger, formatter, repo_root)
    root_logger.setLevel(level)


def _maybe_add_file_handler(
    target_logger: logging.Logger,
    formatter: logging.Formatter,
    repo_root: Optional[Path],
) -> None:
    if repo_root is None:
        return
    sciona_dir = Path(repo_root) / setup_config.SCIONA_DIR_NAME
    if not sciona_dir.exists():
        return
    log_path = _resolve_log_path(repo_root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path_str = str(log_path)
    for handler in target_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            if getattr(handler, "baseFilename", None) == log_path_str:
                return
    file_handler = logging.FileHandler(log_path_str, encoding="utf-8")
    file_handler.setFormatter(formatter)
    target_logger.addHandler(file_handler)


def _resolve_log_path(repo_root: Path) -> Path:
    repo_root = Path(repo_root)
    sciona_dir = repo_root / setup_config.SCIONA_DIR_NAME
    if setup_config.LOG_DIRNAME:
        return sciona_dir / setup_config.LOG_DIRNAME / setup_config.LOG_FILENAME
    return sciona_dir / setup_config.LOG_FILENAME


def debug_enabled() -> bool:
    return _DEBUG_ENABLED
