# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Default runtime policy values."""

from __future__ import annotations

LANGUAGE_DEFAULTS = {
    "python": {"enabled": False},
    "typescript": {"enabled": False},
    "java": {"enabled": False},
}
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_DEBUG = False
DEFAULT_LOG_STRUCTURED = False
DEFAULT_LOG_MODULE_LEVELS: dict[str, str] = {}
DEFAULT_DB_TIMEOUT = 120.0
DEFAULT_GIT_TIMEOUT = 30.0

__all__ = [
    "LANGUAGE_DEFAULTS",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_LOG_DEBUG",
    "DEFAULT_LOG_STRUCTURED",
    "DEFAULT_LOG_MODULE_LEVELS",
    "DEFAULT_DB_TIMEOUT",
    "DEFAULT_GIT_TIMEOUT",
]
