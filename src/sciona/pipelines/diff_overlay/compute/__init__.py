# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay computation helpers."""

from __future__ import annotations

from .summary import summarize_overlay
from .core import (
    _ChangeSet,
    analyze_files,
    build_file_records,
    build_node_lookup,
    collect_changes,
    compute_overlay_rows,
    filter_excluded_paths,
    ingest_status,
)
from .payloads import (
    edge_key,
    edge_payload,
    node_content_hash,
    node_payload,
    overlay_row,
)
from .config import (
    analyzers_by_language,
    discovery_excludes,
    resolve_enabled_languages,
    worktree_fingerprint,
)

__all__ = [
    "analyze_files",
    "analyzers_by_language",
    "build_file_records",
    "build_node_lookup",
    "collect_changes",
    "compute_overlay_rows",
    "discovery_excludes",
    "edge_key",
    "edge_payload",
    "resolve_enabled_languages",
    "ingest_status",
    "node_content_hash",
    "node_payload",
    "overlay_row",
    "worktree_fingerprint",
]
