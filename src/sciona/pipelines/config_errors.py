# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Pipeline configuration errors."""

from __future__ import annotations

from ...runtime.errors import ConfigError, EnvError

RuntimeEnvError = EnvError
RuntimeConfigError = ConfigError

__all__ = ["RuntimeEnvError", "RuntimeConfigError", "ConfigError", "EnvError"]
