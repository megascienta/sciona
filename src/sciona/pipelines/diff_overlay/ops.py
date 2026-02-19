# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dirty-worktree diff overlay helpers for reducer payloads."""

from __future__ import annotations

from .ops_get import _OVERLAY_PROFILE, get_overlay, overlay_bundle_exists
from .ops_patch import (
    _resolve_projection,
    apply_overlay_to_text,
    attach_unavailable_overlay,
)
from .ops_sort import (
    _call_sort_key,
    _edge_sort_key,
    _node_sort_key,
    _parse_entry_payload,
    _sort_change_entries,
    rows_to_payload,
)

__all__ = [
    "apply_overlay_to_text",
    "get_overlay",
]
