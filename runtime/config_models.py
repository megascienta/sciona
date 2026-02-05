"""Typed runtime configuration models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence


@dataclass(frozen=True)
class LanguageSettings:
    name: str
    enabled: bool


@dataclass(frozen=True)
class DiscoverySettings:
    exclude_globs: list[str]


@dataclass(frozen=True)
class DatabaseSettings:
    timeout: float


@dataclass(frozen=True)
class GitSettings:
    timeout: float


@dataclass(frozen=True)
class RuntimeConfig:
    languages: Dict[str, LanguageSettings]
    discovery: DiscoverySettings
    database: DatabaseSettings
    git: GitSettings


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
    endpoint_allowlist: Sequence[str]
    allow_api_key_for_custom_endpoint: bool
    temperature: float
    supported_models: Sequence[str]
    timeout: float
    max_retries: int


@dataclass(frozen=True)
class ScionaConfig:
    runtime: RuntimeConfig
    llm: LLMSettings
    logging: LoggingSettings


__all__ = [
    "LanguageSettings",
    "DiscoverySettings",
    "RuntimeConfig",
    "LoggingSettings",
    "LLMSettings",
    "DatabaseSettings",
    "GitSettings",
    "ScionaConfig",
]
