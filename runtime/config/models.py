# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Typed runtime configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


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
class ScionaConfig:
    runtime: RuntimeConfig
    logging: LoggingSettings


__all__ = [
    "LanguageSettings",
    "DiscoverySettings",
    "RuntimeConfig",
    "LoggingSettings",
    "DatabaseSettings",
    "GitSettings",
    "ScionaConfig",
]
