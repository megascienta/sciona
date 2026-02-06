# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Package version helpers."""

from __future__ import annotations

from .runtime.constants import TOOL_VERSION

__version__ = TOOL_VERSION

__all__ = ["TOOL_VERSION", "__version__"]
