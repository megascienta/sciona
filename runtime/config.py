"""Immutable configuration for SCIONA runtime."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import yaml

from .config_defaults import (
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_DB_TIMEOUT,
    DEFAULT_GIT_TIMEOUT,
    DEFAULT_LOG_DEBUG,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_MODULE_LEVELS,
    DEFAULT_LOG_STRUCTURED,
    DEFAULT_LLM_MAX_RETRIES,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_RETENTION_K,
    DEFAULT_TEMPERATURE,
    LANGUAGE_DEFAULTS,
)
from .errors import ConfigError
from .paths import get_config_path



@dataclass(frozen=True)
class LanguageSettings:
    name: str
    enabled: bool


@dataclass(frozen=True)
class DiscoverySettings:
    exclude_globs: list[str]


@dataclass(frozen=True)
class SnapshotPolicy:
    retention_committed: int


@dataclass(frozen=True)
class RuntimeConfig:
    languages: Dict[str, LanguageSettings]
    discovery: DiscoverySettings
    snapshot_policy: SnapshotPolicy
    database: "DatabaseSettings"
    git: "GitSettings"


@dataclass(frozen=True)
class LoggingSettings:
    level: str
    module_levels: Dict[str, str]
    debug: bool
    structured: bool


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    api_endpoint: Optional[str]
    api_key: Optional[str]
    temperature: float
    supported_models: Sequence[str]
    timeout: float
    max_retries: int


@dataclass(frozen=True)
class DatabaseSettings:
    timeout: float


@dataclass(frozen=True)
class GitSettings:
    timeout: float


@dataclass(frozen=True)
class ScionaConfig:
    runtime: RuntimeConfig
    llm: LLMSettings
    logging: LoggingSettings


def _load_raw_config(repo_root: Path) -> Dict[str, Any]:
    config_path = get_config_path(repo_root)
    if not config_path.exists():
        raise ConfigError(
            "Missing .sciona/config.yaml. Run 'sciona init' and edit the generated template before building.",
            code="missing_config",
            hint="Run `sciona init` and edit .sciona/config.yaml to enable languages.",
        )
    try:
        raw_text = config_path.read_text(encoding="utf-8")
        if len(raw_text.encode("utf-8")) > 1_000_000:
            raise ConfigError(
                "Config file too large.",
                code="invalid_config",
                hint="Reduce .sciona/config.yaml size.",
            )
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(
            "Failed to parse .sciona/config.yaml",
            code="invalid_config",
            hint="Fix the YAML syntax in .sciona/config.yaml.",
        ) from exc
    if not isinstance(data, dict):
        return {}
    return data


def _coerce_int(block: Dict[str, Any], key: str, default: int) -> int:
    try:
        return int(block.get(key, default))
    except (TypeError, ValueError):
        return default


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


def _load_language_settings(repo_root: Path) -> Dict[str, LanguageSettings]:
    raw_config = _load_raw_config(repo_root)
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


def _snapshot_policy(data: Dict[str, Any]) -> SnapshotPolicy:
    retention = data.get("retention_committed", DEFAULT_RETENTION_K)
    try:
        retention_value = int(retention)
    except (TypeError, ValueError):
        retention_value = DEFAULT_RETENTION_K
    if retention_value < 1:
        retention_value = DEFAULT_RETENTION_K
    return SnapshotPolicy(retention_committed=retention_value)


def _load_runtime_config(repo_root: Path) -> RuntimeConfig:
    raw = _load_raw_config(repo_root)
    languages = _load_language_settings(repo_root)
    discovery = _load_discovery_settings(raw)
    policies_block = raw.get("policies", {}) if isinstance(raw, dict) else {}
    snapshot_policy = _snapshot_policy(policies_block.get("snapshots", {}))
    database = _load_database_settings(raw)
    git = _load_git_settings(raw)
    return RuntimeConfig(
        languages=languages,
        discovery=discovery,
        snapshot_policy=snapshot_policy,
        database=database,
        git=git,
    )


def _load_logging_settings(repo_root: Path, *, allow_missing: bool = False) -> LoggingSettings:
    try:
        raw = _load_raw_config(repo_root)
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


def _load_llm_settings(repo_root: Path) -> LLMSettings:
    raw = _load_raw_config(repo_root)
    llm_block = raw.get("llm", {}) if isinstance(raw, dict) else {}
    if not isinstance(llm_block, dict):
        llm_block = {}

    supported_models_raw = llm_block.get("supported_models", [])
    if not isinstance(supported_models_raw, list):
        supported_models_raw = []
    supported_models = tuple(str(entry) for entry in supported_models_raw if entry)
    timeout = _coerce_float(llm_block, "timeout", DEFAULT_LLM_TIMEOUT)
    if timeout <= 0:
        timeout = DEFAULT_LLM_TIMEOUT
    max_retries = _coerce_int(llm_block, "max_retries", DEFAULT_LLM_MAX_RETRIES)
    if max_retries < 0:
        max_retries = DEFAULT_LLM_MAX_RETRIES
    llm = LLMSettings(
        provider=str(llm_block.get("provider", DEFAULT_LLM_PROVIDER) or DEFAULT_LLM_PROVIDER),
        model=str(llm_block.get("model", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL),
        api_endpoint=llm_block.get("api_endpoint"),
        api_key=llm_block.get("api_key"),
        temperature=_coerce_float(llm_block, "temperature", DEFAULT_TEMPERATURE),
        supported_models=supported_models,
        timeout=timeout,
        max_retries=max_retries,
    )
    if llm.supported_models and llm.model not in llm.supported_models:
        raise ConfigError(
            f"Configured LLM model '{llm.model}' is not in supported_models.",
            code="invalid_llm_model",
        )
    return llm


@lru_cache(maxsize=4)
def load_sciona_config(repo_root: Path) -> ScionaConfig:
    runtime_cfg = _load_runtime_config(repo_root)
    llm_cfg = _load_llm_settings(repo_root)
    logging_cfg = _load_logging_settings(repo_root)
    return ScionaConfig(
        runtime=runtime_cfg,
        llm=llm_cfg,
        logging=logging_cfg,
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
    "SnapshotPolicy",
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
