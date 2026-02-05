"""Immutable runtime config loaders and cache boundary."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict

from .config_models import (
    DatabaseSettings,
    DiscoverySettings,
    GitSettings,
    LLMSettings,
    LanguageSettings,
    LoggingSettings,
    RuntimeConfig,
    ScionaConfig,
)
from .config_parse import (
    load_language_settings as _load_language_settings,
    load_llm_settings as _load_llm_settings,
    load_logging_settings as _load_logging_settings,
    load_runtime_config as _load_runtime_config,
)


@lru_cache(maxsize=4)
def load_sciona_config(repo_root: Path) -> ScionaConfig:
    return ScionaConfig(
        runtime=_load_runtime_config(repo_root),
        llm=_load_llm_settings(repo_root),
        logging=_load_logging_settings(repo_root),
    )


@lru_cache(maxsize=4)
def _cached_llm_settings(repo_root: Path) -> LLMSettings:
    return _load_llm_settings(repo_root)


@lru_cache(maxsize=4)
def _cached_logging_settings(repo_root: Path) -> LoggingSettings:
    return _load_logging_settings(repo_root)


def load_runtime_config(repo_root: Path) -> RuntimeConfig:
    return load_sciona_config(repo_root).runtime


def load_llm_settings(repo_root: Path) -> LLMSettings:
    return _cached_llm_settings(repo_root)


def load_logging_settings(repo_root: Path, *, allow_missing: bool = False) -> LoggingSettings:
    if allow_missing:
        return _load_logging_settings(repo_root, allow_missing=True)
    return _cached_logging_settings(repo_root)


def load_language_settings(repo_root: Path) -> Dict[str, LanguageSettings]:
    return load_sciona_config(repo_root).runtime.languages


def load_discovery_settings(repo_root: Path) -> DiscoverySettings:
    return load_sciona_config(repo_root).runtime.discovery


__all__ = [
    "LanguageSettings",
    "DiscoverySettings",
    "RuntimeConfig",
    "LoggingSettings",
    "LLMSettings",
    "DatabaseSettings",
    "GitSettings",
    "ScionaConfig",
    "load_llm_settings",
    "load_discovery_settings",
    "load_language_settings",
    "load_logging_settings",
    "load_runtime_config",
    "load_sciona_config",
]
