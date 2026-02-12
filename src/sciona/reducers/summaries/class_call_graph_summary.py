# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Class-level call graph reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..helpers import queries
from ..helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ..helpers.artifact_graph_rollups import load_class_call_edges
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="class_call_graph_summary",
    category="dependency",
    scope="class",
    placeholders=("CLASS_CALL_GRAPH",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Class-level call graph summary.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    class_id: str | None = None,
    method_id: str | None = None,
    top_k: int | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="class_call_graph_summary reducer"
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

    limit = _normalize_top_k(top_k)

    outgoing_edges = load_class_call_edges(
        repo_root,
        src_class_ids=[resolved_class_id],
    )
    incoming_edges = load_class_call_edges(
        repo_root,
        dst_class_ids=[resolved_class_id],
    )

    class_ids = {resolved_class_id}
    for src_id, dst_id, _count in outgoing_edges + incoming_edges:
        class_ids.add(src_id)
        class_ids.add(dst_id)
    name_lookup = _class_name_lookup(conn, snapshot_id, class_ids)

    outgoing_all = _edges_to_entries(
        outgoing_edges, direction="outgoing", name_lookup=name_lookup
    )
    incoming_all = _edges_to_entries(
        incoming_edges, direction="incoming", name_lookup=name_lookup
    )
    outgoing = _apply_top_k(outgoing_all, limit)
    incoming = _apply_top_k(incoming_all, limit)

    body = {
        "class_id": resolved_class_id,
        "outgoing_count": len(outgoing),
        "incoming_count": len(incoming),
        "outgoing_total": len(outgoing_all),
        "incoming_total": len(incoming_all),
        "outgoing_coverage_ratio": _coverage_ratio(len(outgoing), len(outgoing_all)),
        "incoming_coverage_ratio": _coverage_ratio(len(incoming), len(incoming_all)),
        "total_edges": len(outgoing_all) + len(incoming_all),
        "edge_summary": {
            "CALLS": {
                "outgoing": len(outgoing_all),
                "incoming": len(incoming_all),
            }
        },
        "top_k": limit,
        "outgoing": outgoing,
        "incoming": incoming,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }
    return render_json_payload(body)


def _edges_to_entries(
    edges: List[tuple[str, str, int]],
    *,
    direction: str,
    name_lookup: Dict[str, str],
) -> List[Dict[str, int | str]]:
    entries: List[Dict[str, int | str]] = []
    for src_id, dst_id, count in edges:
        entries.append(
            {
                "src_class_id": src_id,
                "dst_class_id": dst_id,
                "src_class_qualified_name": name_lookup.get(src_id),
                "dst_class_qualified_name": name_lookup.get(dst_id),
                "direction": direction,
                "call_count": count,
            }
        )
    entries.sort(
        key=lambda item: (
            -int(item["call_count"]),
            str(item["src_class_id"]),
            str(item["dst_class_id"]),
        )
    )
    return entries


def _class_name_lookup(
    conn, snapshot_id: str, class_ids: set[str]
) -> Dict[str, str]:
    if not class_ids:
        return {}
    placeholders = ",".join("?" for _ in class_ids)
    rows = conn.execute(
        f"""
        SELECT ni.structural_id, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'class'
          AND ni.structural_id IN ({placeholders})
        """,
        (snapshot_id, *class_ids),
    ).fetchall()
    return {
        row["structural_id"]: row["qualified_name"]
        for row in rows
        if row["qualified_name"]
    }


def _normalize_top_k(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    value = int(value)
    if value <= 0:
        raise ValueError("class_call_graph_summary top_k must be a positive integer.")
    return value


def _apply_top_k(
    entries: List[Dict[str, int | str]], top_k: Optional[int]
) -> List[Dict[str, int | str]]:
    if top_k is None:
        return entries
    return entries[:top_k]


def _coverage_ratio(selected: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return round(selected / total, 4)
