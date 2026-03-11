# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility exports for shared reducer utility helpers."""

from __future__ import annotations

from .counters import top_modules
from .snapshot_guard import require_latest_committed_snapshot
from .source_files import line_span_hash, resolve_repo_file

__all__ = [
    "line_span_hash",
    "require_latest_committed_snapshot",
    "resolve_repo_file",
    "top_modules",
]
