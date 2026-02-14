# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callsite index reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..helpers import queries
from ..helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="callsite_index",
    category="dependency",
    scope="callable",
    placeholders=("CALLSITE_INDEX",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Indexed caller/callee edges for a callable, including callsite details. " \
    "Use when reasoning about call directionality or callsite-level analysis. " \
    "Scope: callable-level call edges.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    direction: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="callsite_index reducer"
    )
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    if method_id:
        resolved_id = queries.resolve_method_id(conn, snapshot_id, method_id)
    else:
        resolved_id = queries.resolve_function_id(conn, snapshot_id, function_id)
    dir_value = _normalize_direction(direction)
    artifact_available = artifact_db_available(repo_root) if repo_root else False
    edges = _load_edges(repo_root, snapshot_id, resolved_id, dir_value)
    node_ids = {edge["caller_id"] for edge in edges} | {
        edge["callee_id"] for edge in edges
    }
    lookup = _node_lookup(conn, snapshot_id, node_ids)
    module_lookup = queries.module_id_lookup(conn, snapshot_id)
    enriched = []
    for edge in edges:
        caller = lookup.get(edge["caller_id"], {})
        callee = lookup.get(edge["callee_id"], {})
        enriched.append(
            {
                "caller_id": edge["caller_id"],
                "callee_id": edge["callee_id"],
                "caller_qualified_name": caller.get("qualified_name"),
                "callee_qualified_name": callee.get("qualified_name"),
                "caller_file_path": caller.get("file_path"),
                "callee_file_path": callee.get("file_path"),
                "caller_language": caller.get("language"),
                "callee_language": callee.get("language"),
                "caller_node_type": caller.get("node_type"),
                "callee_node_type": callee.get("node_type"),
                "caller_module_qualified_name": module_lookup.get(edge["caller_id"]),
                "callee_module_qualified_name": module_lookup.get(edge["callee_id"]),
                "edge_kind": edge["edge_kind"],
                "edge_source": edge.get("edge_source"),
                "call_hash": edge.get("call_hash"),
                "line_span": None,
            }
        )
    body = {
        "callable_id": resolved_id,
        "direction": dir_value,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
        "edge_count": len(enriched),
        "edges": enriched,
    }
    return render_json_payload(body)


def _normalize_direction(direction: Optional[str]) -> str:
    if not direction:
        return "both"
    value = str(direction).strip().lower()
    if value in {"in", "out", "both"}:
        return value
    raise ValueError("callsite_index direction must be one of: in, out, both.")


def _load_edges(
    repo_root,
    snapshot_id: str,
    resolved_id: str,
    direction: str,
) -> List[Dict[str, str]]:
    if repo_root is None:
        return []
    if direction in {"out", "both"}:
        outgoing = load_artifact_edges(
            repo_root,
            edge_kinds=["CALLS"],
            src_ids=[resolved_id],
        )
    else:
        outgoing = []
    if direction in {"in", "both"}:
        incoming = load_artifact_edges(
            repo_root,
            edge_kinds=["CALLS"],
            dst_ids=[resolved_id],
        )
    else:
        incoming = []
    edges: List[Dict[str, str]] = []
    for src, dst, edge_kind in outgoing:
        edges.append(
            {
                "caller_id": src,
                "callee_id": dst,
                "edge_kind": edge_kind,
                "edge_source": "artifact_db",
                "call_hash": None,
            }
        )
    for src, dst, edge_kind in incoming:
        edges.append(
            {
                "caller_id": src,
                "callee_id": dst,
                "edge_kind": edge_kind,
                "edge_source": "artifact_db",
                "call_hash": None,
            }
        )
    return edges


def _node_lookup(
    conn, snapshot_id: str, node_ids: set[str]
) -> Dict[str, Dict[str, str]]:
    if not node_ids:
        return {}
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id, sn.node_type, sn.language, ni.qualified_name, ni.file_path
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
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
            "language": row["language"],
            "node_type": row["node_type"],
        }
        for row in rows
    }
