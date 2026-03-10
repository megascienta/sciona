# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""SCIONA package entrypoint."""

from __future__ import annotations

from . import api
from .runtime.common.constants import TOOL_VERSION

__version__ = TOOL_VERSION

__all__ = ["TOOL_VERSION", "__version__", "api"]
