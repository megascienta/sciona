# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callable call graph reducer."""

from __future__ import annotations

from typing import Dict, List

from ...code_analysis.analysis.orderings import order_nodes
from ..helpers import queries
from ..helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="call_graph",
    category="dependency",
    scope="callable",
    placeholders=("CALL_GRAPH",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Caller/callee call graph for a callable.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="call_graph reducer"
    )
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    if method_id:
        resolved_id = queries.resolve_method_id(conn, snapshot_id, method_id)
    else:
        resolved_id = queries.resolve_function_id(conn, snapshot_id, function_id)
    artifact_available = artifact_db_available(repo_root) if repo_root else False
    outgoing_edges = load_artifact_edges(
        repo_root,
        edge_kinds=["CALLS"],
        src_ids=[resolved_id],
    )
    incoming_edges = load_artifact_edges(
        repo_root,
        edge_kinds=["CALLS"],
        dst_ids=[resolved_id],
    )
    callee_ids = sorted({dst for _, dst, _ in outgoing_edges})
    caller_ids = sorted({src for src, _, _ in incoming_edges})
    callees = _fetch_nodes(conn, snapshot_id, callee_ids)
    callers = _fetch_nodes(conn, snapshot_id, caller_ids)
    order_nodes(callees, key="qualified_name")
    order_nodes(callers, key="qualified_name")
    body = {
        "callable_id": resolved_id,
        "caller_count": len(callers),
        "callee_count": len(callees),
        "callers": callers,
        "callees": callees,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }
    return render_json_payload(body)


def _fetch_nodes(conn, snapshot_id: str, node_ids: List[str]) -> List[Dict[str, str]]:
    if not node_ids:
        return []
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id, sn.node_type, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
            AND ni.snapshot_id = ?
        WHERE sn.structural_id IN ({placeholders})
        """,
        (snapshot_id, *node_ids),
    ).fetchall()
    return [
        {
            "structural_id": row["structural_id"],
            "qualified_name": row["qualified_name"],
            "node_type": row["node_type"],
        }
        for row in rows
        if row["qualified_name"]
    ]
