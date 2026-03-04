# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Symbol reference reducer."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ...helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ...helpers.render import render_json_payload, require_connection
from ...helpers.utils import require_latest_committed_snapshot
from ...metadata import ReducerMeta

def _build_references(
    conn,
    repo_root,
    snapshot_id: str,
    matches: List[Dict[str, object]],
    lookup: Dict[str, Dict[str, str]],
) -> List[Dict[str, object]]:
    callable_ids = [
        match["structural_id"]
        for match in matches
        if match["node_type"] == "callable"
    ]
    module_ids = [
        match["structural_id"] for match in matches if match["node_type"] == "module"
    ]
    references: List[Dict[str, object]] = []
    if callable_ids:
        references.extend(
            _call_references(conn, repo_root, snapshot_id, callable_ids, lookup)
        )
    if module_ids:
        references.extend(_import_references(conn, snapshot_id, module_ids, lookup))
    references.sort(
        key=lambda item: (
            str(item.get("symbol_id")),
            str(item.get("reference_kind")),
            str(item.get("direction")),
            str(item.get("edge_kind")),
            str(item.get("other_id")),
        )
    )
    return references

def _call_references(
    conn,
    repo_root,
    snapshot_id: str,
    callable_ids: List[str],
    lookup: Dict[str, Dict[str, str]],
) -> List[Dict[str, object]]:
    if repo_root is None:
        return []
    outgoing = load_artifact_edges(
        repo_root,
        edge_kinds=["CALLS"],
        src_ids=callable_ids,
    )
    incoming = load_artifact_edges(
        repo_root,
        edge_kinds=["CALLS"],
        dst_ids=callable_ids,
    )
    refs: List[Dict[str, object]] = []
    all_ids = (
        {src for src, _, _ in outgoing}
        | {dst for _, dst, _ in outgoing}
        | {src for src, _, _ in incoming}
        | {dst for _, dst, _ in incoming}
    )
    lookup = {**lookup, **_node_lookup(conn, snapshot_id, set(all_ids))}
    for src, dst, edge_kind in outgoing:
        other = lookup.get(dst, {})
        refs.append(
            {
                "symbol_id": src,
                "reference_kind": "call",
                "direction": "out",
                "edge_kind": edge_kind,
                "other_id": dst,
                "other_qualified_name": other.get("qualified_name"),
                "other_node_type": other.get("node_type"),
                "other_file_path": other.get("file_path"),
            }
        )
    for src, dst, edge_kind in incoming:
        other = lookup.get(src, {})
        refs.append(
            {
                "symbol_id": dst,
                "reference_kind": "call",
                "direction": "in",
                "edge_kind": edge_kind,
                "other_id": src,
                "other_qualified_name": other.get("qualified_name"),
                "other_node_type": other.get("node_type"),
                "other_file_path": other.get("file_path"),
            }
        )
    return refs

def _import_references(
    conn,
    snapshot_id: str,
    module_ids: List[str],
    lookup: Dict[str, Dict[str, str]],
) -> List[Dict[str, object]]:
    if not module_ids:
        return []
    placeholders = ",".join("?" for _ in module_ids)
    rows = conn.execute(
        f"""
        SELECT e.src_structural_id,
               e.dst_structural_id,
               e.edge_type
        FROM edges e
        WHERE e.snapshot_id = ?
          AND e.edge_type = 'IMPORTS_DECLARED'
          AND (e.src_structural_id IN ({placeholders}) OR e.dst_structural_id IN ({placeholders}))
        ORDER BY e.src_structural_id, e.dst_structural_id
        """,
        (snapshot_id, *module_ids, *module_ids),
    ).fetchall()
    refs: List[Dict[str, object]] = []
    all_ids = {row["src_structural_id"] for row in rows} | {
        row["dst_structural_id"] for row in rows
    }
    lookup = {**lookup, **_node_lookup(conn, snapshot_id, set(all_ids))}
    for row in rows:
        src = row["src_structural_id"]
        dst = row["dst_structural_id"]
        edge_kind = row["edge_type"]
        if src in module_ids:
            other = lookup.get(dst, {})
            refs.append(
                {
                    "symbol_id": src,
                    "reference_kind": "import",
                    "direction": "out",
                    "edge_kind": edge_kind,
                    "other_id": dst,
                    "other_qualified_name": other.get("qualified_name"),
                    "other_node_type": other.get("node_type"),
                    "other_file_path": other.get("file_path"),
                }
            )
        if dst in module_ids:
            other = lookup.get(src, {})
            refs.append(
                {
                    "symbol_id": dst,
                    "reference_kind": "import",
                    "direction": "in",
                    "edge_kind": edge_kind,
                    "other_id": src,
                    "other_qualified_name": other.get("qualified_name"),
                    "other_node_type": other.get("node_type"),
                    "other_file_path": other.get("file_path"),
                }
            )
    return refs

def _node_lookup(
    conn, snapshot_id: str, node_ids: set[str]
) -> Dict[str, Dict[str, str]]:
    if not node_ids:
        return {}
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id,
               sn.node_type,
               ni.qualified_name,
               ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
            AND ni.snapshot_id = ?
        WHERE sn.structural_id IN ({placeholders})
        """,
        (snapshot_id, *node_ids),
    ).fetchall()
    return {
        row["structural_id"]: {
            "node_type": row["node_type"],
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
        if row["qualified_name"]
    }
