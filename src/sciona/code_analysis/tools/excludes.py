# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for workspace exclusion helpers."""

from __future__ import annotations

from .workspace.excludes import build_exclude_spec, is_excluded_path, is_hard_excluded

__all__ = ["build_exclude_spec", "is_excluded_path", "is_hard_excluded"]
