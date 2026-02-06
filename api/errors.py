# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Public error types (stable)."""

from __future__ import annotations

from ..pipelines.errors import ConfigError
from ..runtime.errors import ScionaError

__all__ = ["ScionaError", "ConfigError"]
