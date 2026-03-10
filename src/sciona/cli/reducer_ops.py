# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI facade for reducer registry and emission helpers."""

from __future__ import annotations

from ..pipelines.ops import reducers as _reducer_ops

emit = _reducer_ops.emit
list_entries = _reducer_ops.list_entries
get_entry = _reducer_ops.get_entry
freeze_registry = _reducer_ops.freeze_registry
get_reducers = _reducer_ops.get_reducers
load_reducer = _reducer_ops.load_reducer

__all__ = [
    "emit",
    "list_entries",
    "get_entry",
    "freeze_registry",
    "get_reducers",
    "load_reducer",
]
