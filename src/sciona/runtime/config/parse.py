# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Runtime config parsing/coercion helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .defaults import (
    DEFAULT_DB_TIMEOUT,
    DEFAULT_GIT_TIMEOUT,
    DEFAULT_LOG_DEBUG,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_MODULE_LEVELS,
    DEFAULT_LOG_STRUCTURED,
    LANGUAGE_DEFAULTS,
)
from .io import load_raw_config
from .models import (
    DatabaseSettings,
    DiscoverySettings,
    GitSettings,
    LanguageSettings,
    LoggingSettings,
    RuntimeConfig,
)
from ..errors import ConfigError


def _coerce_float(block: Dict[str, Any], key: str, default: float) -> float:
    try:
        return float(block.get(key, default))
    except (TypeError, ValueError):
        return default


def _coerce_bool(block: Dict[str, Any], key: str, default: bool) -> bool:
    value = block.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes"}:
            return True
        if lowered in {"0", "false", "no"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def load_language_settings(repo_root: Path) -> Dict[str, LanguageSettings]:
    raw_config = load_raw_config(repo_root)
    lang_block = raw_config.get("languages", {}) if isinstance(raw_config, dict) else {}
    resolved: Dict[str, LanguageSettings] = {}
    for name, lang_defaults in LANGUAGE_DEFAULTS.items():
        user_cfg = lang_block.get(name, {}) if isinstance(lang_block, dict) else {}
        enabled = bool(user_cfg.get("enabled", lang_defaults["enabled"]))
        resolved[name] = LanguageSettings(name=name, enabled=enabled)
    if not any(settings.enabled for settings in resolved.values()):
        raise ConfigError(
            "No languages enabled in .sciona/config.yaml. Edit the config to enable at least one language.",
            code="missing_languages",
        )
    return resolved


def _load_discovery_settings(raw: Dict[str, Any]) -> DiscoverySettings:
    discovery_block = raw.get("discovery", {}) if isinstance(raw, dict) else {}
    exclude_globs = discovery_block.get("exclude_globs", [])
    if not isinstance(exclude_globs, list):
        exclude_globs = []
    cleaned = [str(entry) for entry in exclude_globs if entry]
    return DiscoverySettings(exclude_globs=cleaned)


def _load_database_settings(raw: Dict[str, Any]) -> DatabaseSettings:
    database_block = raw.get("database", {}) if isinstance(raw, dict) else {}
    timeout = _coerce_float(database_block, "timeout", DEFAULT_DB_TIMEOUT)
    if timeout <= 0:
        timeout = DEFAULT_DB_TIMEOUT
    return DatabaseSettings(timeout=timeout)


def _load_git_settings(raw: Dict[str, Any]) -> GitSettings:
    git_block = raw.get("git", {}) if isinstance(raw, dict) else {}
    timeout = _coerce_float(git_block, "timeout", DEFAULT_GIT_TIMEOUT)
    if timeout <= 0:
        timeout = DEFAULT_GIT_TIMEOUT
    return GitSettings(timeout=timeout)


def load_runtime_config(repo_root: Path) -> RuntimeConfig:
    raw = load_raw_config(repo_root)
    return RuntimeConfig(
        languages=load_language_settings(repo_root),
        discovery=_load_discovery_settings(raw),
        database=_load_database_settings(raw),
        git=_load_git_settings(raw),
    )


def load_logging_settings(
    repo_root: Path, *, allow_missing: bool = False
) -> LoggingSettings:
    try:
        raw = load_raw_config(repo_root)
    except ConfigError:
        if not allow_missing:
            raise
        raw = {}
    logging_block = raw.get("logging", {}) if isinstance(raw, dict) else {}
    level = logging_block.get("level", DEFAULT_LOG_LEVEL) or DEFAULT_LOG_LEVEL
    debug = _coerce_bool(logging_block, "debug", DEFAULT_LOG_DEBUG)
    structured = _coerce_bool(logging_block, "structured", DEFAULT_LOG_STRUCTURED)
    module_levels_raw = logging_block.get("module_levels", DEFAULT_LOG_MODULE_LEVELS)
    module_levels: Dict[str, str] = {}
    if isinstance(module_levels_raw, dict):
        for key, value in module_levels_raw.items():
            if not key:
                continue
            module_levels[str(key)] = str(value)
    return LoggingSettings(
        level=str(level),
        module_levels=module_levels,
        debug=debug,
        structured=structured,
    )


__all__ = [
    "load_language_settings",
    "load_logging_settings",
    "load_runtime_config",
]
