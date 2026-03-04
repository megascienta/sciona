# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CoreDB read operations."""

from __future__ import annotations

from .read_ops_snapshots import (
    count_committed_snapshots,
    latest_committed_snapshot,
    latest_committed_snapshot_id,
    list_committed_snapshots,
    snapshot_created_at,
    snapshot_exists,
    snapshot_git_commit_sha,
    snapshot_is_committed,
    validate_snapshot_for_read,
)
from .read_ops_nodes import (
    caller_language_map,
    language_file_node_counts,
    list_nodes_by_types,
    list_nodes_with_names,
    list_structural_nodes,
    lookup_node_instances,
    lookup_structural_id,
    node_instances_for_file_paths,
    search_node_instances,
)
from .read_ops_edges import (
    edges_for_source_ids,
    language_edge_counts,
    list_edges,
    list_edges_by_type,
)
from .read_ops_hashes import (
    node_hashes_for_ids,
    snapshot_node_hashes,
    structural_hash_edge_entries,
    structural_hash_node_entries,
)

__all__ = [
    "latest_committed_snapshot",
    "latest_committed_snapshot_id",
    "snapshot_git_commit_sha",
    "snapshot_created_at",
    "count_committed_snapshots",
    "list_committed_snapshots",
    "lookup_node_instances",
    "lookup_structural_id",
    "search_node_instances",
    "snapshot_is_committed",
    "snapshot_exists",
    "validate_snapshot_for_read",
    "snapshot_node_hashes",
    "node_hashes_for_ids",
    "list_structural_nodes",
    "list_edges",
    "list_nodes_with_names",
    "list_edges_by_type",
    "list_nodes_by_types",
    "node_instances_for_file_paths",
    "language_file_node_counts",
    "caller_language_map",
    "edges_for_source_ids",
    "language_edge_counts",
    "structural_hash_node_entries",
    "structural_hash_edge_entries",
]
