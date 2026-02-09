# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Class-level call graph reducer."""

from __future__ import annotations

from typing import Dict, List

from ..helpers import queries
from ..helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ..helpers.artifact_graph_rollups import load_class_call_edges
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="class_call_graph",
    category="calls",
    scope="class",
    placeholders=("CLASS_CALL_GRAPH",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="dependency",
    summary="Class-level call graph summary.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    class_id: str | None = None,
    method_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="class_call_graph reducer"
    )
    resolved_class_id = class_id
    if not resolved_class_id and method_id:
        method_structural_id = queries.resolve_method_id(conn, snapshot_id, method_id)
        edges = load_artifact_edges(
            repo_root,
            edge_kinds=["DEFINES_METHOD"],
            dst_ids=[method_structural_id],
        )
        if edges:
            resolved_class_id = edges[0][0]
    if not resolved_class_id:
        raise ValueError("CLASS_CALL_GRAPH requires class_id.")
    artifact_available = artifact_db_available(repo_root) if repo_root else False

    outgoing_edges = load_class_call_edges(
        repo_root,
        snapshot_id=snapshot_id,
        src_class_ids=[resolved_class_id],
    )
    incoming_edges = load_class_call_edges(
        repo_root,
        snapshot_id=snapshot_id,
        dst_class_ids=[resolved_class_id],
    )

    outgoing = _edges_to_entries(outgoing_edges, direction="outgoing")
    incoming = _edges_to_entries(incoming_edges, direction="incoming")

    body = {
        "class_id": resolved_class_id,
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
        class_id = dst_id if direction == "outgoing" else src_id
        entries.append({"class_id": class_id, "call_count": count})
    entries.sort(key=lambda item: (-int(item["call_count"]), str(item["class_id"])))
    return entries
