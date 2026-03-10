# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Addon-facing runtime contracts."""

from .contract import (
    PLUGIN_API_MAJOR,
    PLUGIN_API_MINOR,
    PLUGIN_API_VERSION,
    requirement_compatible,
)

__all__ = [
    "PLUGIN_API_MAJOR",
    "PLUGIN_API_MINOR",
    "PLUGIN_API_VERSION",
    "requirement_compatible",
]
