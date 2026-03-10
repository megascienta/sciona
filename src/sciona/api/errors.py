# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Stable API error boundary for programmatic consumers."""

from __future__ import annotations

from ..pipelines.errors import ConfigError
from ..runtime.errors import ScionaError

__all__ = ["ScionaError", "ConfigError"]
