# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dirty-worktree diff overlay helpers for reducer payloads."""

from __future__ import annotations

from .ops import apply_overlay_to_text, attach_unavailable_overlay, get_overlay

__all__ = [
    "apply_overlay_to_text",
    "attach_unavailable_overlay",
    "get_overlay",
]
