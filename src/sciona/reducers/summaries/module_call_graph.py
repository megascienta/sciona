# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Module-level call graph reducer."""

from __future__ import annotations

from typing import Dict, List

from ..helpers import queries
from ..helpers.artifact_graph_edges import artifact_db_available
from ..helpers.artifact_graph_rollups import load_module_call_edges
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="module_call_graph",
    category="dependency",
    scope="module",
    placeholders=("MODULE_CALL_GRAPH",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Module-level call graph summary.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    class_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="module_call_graph reducer"
    )
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    resolved_module_id = module_id
    if not resolved_module_id and class_id:
        class_structural_id = queries.resolve_class_id(conn, snapshot_id, class_id)
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, class_structural_id
        )
    if not resolved_module_id and method_id:
        method_structural_id = queries.resolve_method_id(conn, snapshot_id, method_id)
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, method_structural_id
        )
    if not resolved_module_id and function_id:
        function_structural_id = queries.resolve_function_id(
            conn, snapshot_id, function_id
        )
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, function_structural_id
        )
    if not resolved_module_id:
        raise ValueError("MODULE_CALL_GRAPH requires a resolvable module_id.")
    artifact_available = artifact_db_available(repo_root) if repo_root else False

    outgoing_edges = load_module_call_edges(
        repo_root,
        src_module_ids=[resolved_module_id],
    )
    incoming_edges = load_module_call_edges(
        repo_root,
        dst_module_ids=[resolved_module_id],
    )

    outgoing = _edges_to_entries(outgoing_edges, direction="outgoing")
    incoming = _edges_to_entries(incoming_edges, direction="incoming")

    body = {
        "module_qualified_name": resolved_module_id,
        "outgoing_count": len(outgoing),
        "incoming_count": len(incoming),
        "outgoing": outgoing,
        "incoming": incoming,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }
    return render_json_payload(body)


def _edges_to_entries(
    edges: List[tuple[str, str, int]], *, direction: str
) -> List[Dict[str, int | str]]:
    entries: List[Dict[str, int | str]] = []
    for src_id, dst_id, count in edges:
        module_name = dst_id if direction == "outgoing" else src_id
        entries.append({"module_qualified_name": module_name, "call_count": count})
    entries.sort(
        key=lambda item: (-int(item["call_count"]), str(item["module_qualified_name"]))
    )
    return entries
