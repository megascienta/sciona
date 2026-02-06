"""Overlay call-edge computation."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ...code_analysis.config import CALLABLE_NODE_TYPES
from ...data_storage.core_db import read_ops as core_read


def compute_call_overlay_rows(
    *,
    snapshot_id: str,
    worktree_hash: str,
    created_at: str,
    core_conn,
    artifact_conn,
    analysis_nodes: list[dict[str, object]],
    analysis_calls: list[dict[str, object]],
    repo_root: Path,
) -> list[dict[str, object]]:
    if not analysis_calls:
        return []
    caller_lookup = {
        (node.get("qualified_name"), node.get("node_type")): node
        for node in analysis_nodes
        if node.get("qualified_name") and node.get("node_type")
    }
    symbol_index = build_symbol_index_for_overlay(core_conn, snapshot_id, analysis_nodes)
    current_edges: set[tuple[str, str]] = set()
    for record in analysis_calls:
        caller_node = caller_lookup.get(
            (record.get("qualified_name"), record.get("node_type"))
        )
        if not caller_node:
            continue
        caller_id = caller_node.get("structural_id")
        if not caller_id:
            continue
        callee_ids, _ = resolve_callees(
            record.get("callee_identifiers") or [],
            symbol_index,
        )
        for callee_id in callee_ids:
            current_edges.add((caller_id, callee_id))

    if not current_edges:
        return []
    caller_ids = sorted({src for src, _ in current_edges})
    all_ids = sorted({src for src, _ in current_edges} | {dst for _, dst in current_edges})
    snapshot_edges = fetch_snapshot_call_edges(artifact_conn, caller_ids)

    added = current_edges - snapshot_edges
    removed = snapshot_edges - current_edges
    if not added and not removed:
        return []

    node_meta = fetch_node_metadata(core_conn, snapshot_id, all_ids, analysis_nodes)
    rows: list[dict[str, object]] = []
    for src_id, dst_id in sorted(added):
        src_meta = node_meta.get(src_id, {})
        dst_meta = node_meta.get(dst_id, {})
        rows.append(
            {
                "snapshot_id": snapshot_id,
                "worktree_hash": worktree_hash,
                "src_structural_id": src_id,
                "dst_structural_id": dst_id,
                "diff_kind": "add",
                "src_node_type": src_meta.get("node_type"),
                "dst_node_type": dst_meta.get("node_type"),
                "src_qualified_name": src_meta.get("qualified_name"),
                "dst_qualified_name": dst_meta.get("qualified_name"),
                "src_file_path": src_meta.get("file_path"),
                "dst_file_path": dst_meta.get("file_path"),
                "created_at": created_at,
            }
        )
    for src_id, dst_id in sorted(removed):
        src_meta = node_meta.get(src_id, {})
        dst_meta = node_meta.get(dst_id, {})
        rows.append(
            {
                "snapshot_id": snapshot_id,
                "worktree_hash": worktree_hash,
                "src_structural_id": src_id,
                "dst_structural_id": dst_id,
                "diff_kind": "remove",
                "src_node_type": src_meta.get("node_type"),
                "dst_node_type": dst_meta.get("node_type"),
                "src_qualified_name": src_meta.get("qualified_name"),
                "dst_qualified_name": dst_meta.get("qualified_name"),
                "src_file_path": src_meta.get("file_path"),
                "dst_file_path": dst_meta.get("file_path"),
                "created_at": created_at,
            }
        )
    return rows


def fetch_snapshot_call_edges(
    artifact_conn, caller_ids: list[str]
) -> set[tuple[str, str]]:
    if not caller_ids:
        return set()
    placeholders = ",".join("?" for _ in caller_ids)
    rows = artifact_conn.execute(
        f"""
        SELECT src_node_id, dst_node_id
        FROM graph_edges
        WHERE edge_kind = 'CALLS'
          AND src_node_id IN ({placeholders})
        """,
        (*caller_ids,),
    ).fetchall()
    return {(row["src_node_id"], row["dst_node_id"]) for row in rows}


def fetch_node_metadata(
    core_conn,
    snapshot_id: str,
    node_ids: list[str],
    analysis_nodes: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    ids_needed = set(node_ids)
    analysis_lookup = {
        node.get("structural_id"): {
            "node_type": node.get("node_type"),
            "qualified_name": node.get("qualified_name"),
            "file_path": node.get("file_path"),
        }
        for node in analysis_nodes
        if node.get("structural_id")
    }
    ids_needed |= set(analysis_lookup.keys())
    if not ids_needed:
        return analysis_lookup
    placeholders = ",".join("?" for _ in ids_needed)
    rows = core_conn.execute(
        f"""
        SELECT sn.structural_id, sn.node_type, ni.qualified_name, ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
           AND ni.snapshot_id = ?
        WHERE sn.structural_id IN ({placeholders})
        """,
        (snapshot_id, *ids_needed),
    ).fetchall()
    result: dict[str, dict[str, object]] = dict(analysis_lookup)
    for row in rows:
        if row["structural_id"] not in result:
            result[row["structural_id"]] = {
                "node_type": row["node_type"],
                "qualified_name": row["qualified_name"],
                "file_path": row["file_path"],
            }
    return result


def build_symbol_index_for_overlay(
    core_conn,
    snapshot_id: str,
    analysis_nodes: list[dict[str, object]],
) -> dict[str, list[str]]:
    rows = core_read.list_nodes_by_types(
        core_conn, snapshot_id, sorted(CALLABLE_NODE_TYPES)
    )
    index: dict[str, list[str]] = {}
    for structural_id, _node_type, qualified_name in rows:
        identifier = simple_identifier(qualified_name)
        if not identifier:
            continue
        index.setdefault(identifier, []).append(structural_id)
    for node in analysis_nodes:
        if node.get("node_type") not in CALLABLE_NODE_TYPES:
            continue
        identifier = simple_identifier(str(node.get("qualified_name", "")))
        structural_id = node.get("structural_id")
        if identifier and structural_id and identifier not in index:
            index.setdefault(identifier, []).append(structural_id)
    return index


def resolve_callees(
    identifiers: Iterable[str],
    symbol_index: dict[str, list[str]],
) -> tuple[set[str], set[str]]:
    resolved_ids: set[str] = set()
    resolved_names: set[str] = set()
    for identifier in identifiers:
        candidates = symbol_index.get(identifier) or []
        if len(candidates) == 1:
            resolved_ids.add(candidates[0])
            resolved_names.add(identifier)
    return resolved_ids, resolved_names


def simple_identifier(qualified_name: str) -> str | None:
    if not qualified_name:
        return None
    parts = qualified_name.rsplit(".", 1)
    return parts[-1] if parts else qualified_name


__all__ = [
    "build_symbol_index_for_overlay",
    "compute_call_overlay_rows",
    "fetch_node_metadata",
    "fetch_snapshot_call_edges",
    "resolve_callees",
    "simple_identifier",
]
