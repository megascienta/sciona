# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for profiling inspector caches."""

from __future__ import annotations

from .profiling.cache import (
    _javascript_inspector_cached,
    _java_inspector_cached,
    _python_inspector_cached,
    _resolve_safe_profile_path,
    _typescript_inspector_cached,
)

__all__ = [
    "_javascript_inspector_cached",
    "_java_inspector_cached",
    "_python_inspector_cached",
    "_resolve_safe_profile_path",
    "_typescript_inspector_cached",
]
