# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for workspace snapshot helpers."""

from __future__ import annotations

from .workspace.snapshots import count_lines_fast, prepare_file_snapshots

__all__ = ["count_lines_fast", "prepare_file_snapshots"]
