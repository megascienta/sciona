# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Module-level call graph reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..helpers import queries
from ..helpers.artifact_graph_edges import artifact_db_available
from ..helpers.artifact_graph_rollups import load_module_call_edges
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="module_call_graph_summary",
    category="analytics",
    scope="module",
    investigation_roles=("relations",),
    risk_tier="normal",
    investigation_stage="relationship_analysis",
    placeholders=("MODULE_CALL_GRAPH",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Summary of call relationships within a module. " \
    "Use for module-level flow or coupling analysis. " \
    "Scope: module call graph. Payload kind: summary.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    callable_id: str | None = None,
    classifier_id: str | None = None,
    top_k: int | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="module_call_graph_summary reducer"
    )
    resolved_module_id = module_id
    if not resolved_module_id and classifier_id:
        classifier_structural_id = queries.resolve_classifier_id(
            conn, snapshot_id, classifier_id
        )
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, classifier_structural_id
        )
    if not resolved_module_id and callable_id:
        callable_structural_id = queries.resolve_callable_id(
            conn, snapshot_id, callable_id
        )
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, callable_structural_id
        )
    if not resolved_module_id:
        raise ValueError("MODULE_CALL_GRAPH requires a resolvable module_id.")
    artifact_available = artifact_db_available(repo_root) if repo_root else False

    limit = _normalize_top_k(top_k)

    outgoing_edges = load_module_call_edges(
        repo_root,
        src_module_ids=[resolved_module_id],
    )
    incoming_edges = load_module_call_edges(
        repo_root,
        dst_module_ids=[resolved_module_id],
    )

    outgoing_all = _edges_to_entries(outgoing_edges, direction="outgoing")
    incoming_all = _edges_to_entries(incoming_edges, direction="incoming")
    outgoing = _apply_top_k(outgoing_all, limit)
    incoming = _apply_top_k(incoming_all, limit)

    body = {
        "payload_kind": "summary",
        "module_qualified_name": resolved_module_id,
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
    edges: List[tuple[str, str, int]], *, direction: str
) -> List[Dict[str, int | str]]:
    entries: List[Dict[str, int | str]] = []
    for src_id, dst_id, count in edges:
        entries.append(
            {
                "src_module_qualified_name": src_id,
                "dst_module_qualified_name": dst_id,
                "direction": direction,
                "call_count": count,
            }
        )
    entries.sort(
        key=lambda item: (
            -int(item["call_count"]),
            str(item["src_module_qualified_name"]),
            str(item["dst_module_qualified_name"]),
        )
    )
    return entries


def _normalize_top_k(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    value = int(value)
    if value <= 0:
        raise ValueError("module_call_graph_summary top_k must be a positive integer.")
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
