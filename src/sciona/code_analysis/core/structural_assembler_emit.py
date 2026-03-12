# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Emission helpers for StructuralAssembler."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, Optional, Tuple

from ...runtime.common import identity as ids
from .normalize_model import EdgeRecord, FileSnapshot, SemanticNodeRecord


def lookup_structural_id(
    language: str,
    node_type: str,
    qualified_name: str,
    local_map: Dict[str, Tuple[str, str]],
    structural_cache: Dict[Tuple[str, str, str], str],
) -> Optional[str]:
    local = local_map.get(qualified_name)
    if local and local[1] == node_type:
        return local[0]
    cache_key = (language, node_type, qualified_name)
    return structural_cache.get(cache_key)


def emit_node_instances(
    conn,
    store,
    snapshot_id: str,
    nodes: Iterable[SemanticNodeRecord],
    file_snapshot: FileSnapshot,
    node_id_map: Dict[str, Tuple[str, str]],
    content_hash_fn: Callable[[SemanticNodeRecord, FileSnapshot], str],
) -> None:
    for node in nodes:
        structural_id = node_id_map[node.qualified_name][0]
        content_hash = content_hash_fn(node, file_snapshot)
        store.insert_node_instance(
            conn,
            instance_id=ids.instance_id(snapshot_id, structural_id),
            structural_id=structural_id,
            snapshot_id=snapshot_id,
            qualified_name=node.qualified_name,
            file_path=node.file_path.as_posix(),
            start_line=node.start_line,
            end_line=node.end_line,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            content_hash=content_hash,
        )


def emit_edges(
    conn,
    store,
    snapshot_id: str,
    edges: Iterable[EdgeRecord],
    node_id_map: Dict[str, Tuple[str, str]],
    structural_cache: Dict[Tuple[str, str, str], str],
    diagnostics: Optional[Dict[str, object]] = None,
) -> None:
    for edge in edges:
        src_id = lookup_structural_id(
            edge.src_language,
            edge.src_node_type,
            edge.src_qualified_name,
            node_id_map,
            structural_cache,
        )
        dst_id = lookup_structural_id(
            edge.dst_language,
            edge.dst_node_type,
            edge.dst_qualified_name,
            node_id_map,
            structural_cache,
        )
        if not src_id or not dst_id:
            if diagnostics is not None:
                diagnostics["unresolved_edges_total"] = (
                    int(diagnostics.get("unresolved_edges_total", 0) or 0) + 1
                )
                unresolved_by_type = diagnostics.setdefault(
                    "unresolved_edges_by_type", {}
                )
                assert isinstance(unresolved_by_type, dict)
                unresolved_by_type[edge.edge_type] = (
                    int(unresolved_by_type.get(edge.edge_type, 0) or 0) + 1
                )
            continue
        store.insert_edge(
            conn,
            snapshot_id=snapshot_id,
            src_structural_id=src_id,
            dst_structural_id=dst_id,
            edge_type=edge.edge_type,
        )


__all__ = ["emit_edges", "emit_node_instances", "lookup_structural_id"]
