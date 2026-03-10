# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for workspace walker helpers."""

from __future__ import annotations

from .workspace.walker import _is_explicitly_excluded, collect_files

__all__ = ["_is_explicitly_excluded", "collect_files"]
