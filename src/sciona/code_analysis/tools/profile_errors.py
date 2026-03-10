# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for profiling errors."""

from __future__ import annotations

from .profiling.errors import QueryCompileError, TreeSitterBootstrapError

__all__ = ["QueryCompileError", "TreeSitterBootstrapError"]
