# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Classifier-level call graph reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..runtime.overlay.patching.analytics import (
    patch_classifier_call_graph_summary,
)
from .helpers.shared import queries
from .helpers.artifact.graph_edges import artifact_db_available
from .helpers.artifact.graph_rollups import load_class_call_edges
from .helpers.shared.context import current_overlay_payload
from .helpers.shared.render import render_json_payload, require_connection
from .helpers.shared.utils import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="classifier_call_graph_summary",
    category="coupling",
    placeholder="CLASSIFIER_CALL_GRAPH",
    summary="Summarize classifier-level artifact call relationships for the committed "
    "snapshot, with optional narrowing by caller or callee classifier. ",
)

def render(
    snapshot_id: str,
    conn,
    repo_root,
    classifier_id: str | None = None,
    caller_id: str | None = None,
    callee_id: str | None = None,
    top_k: int | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="classifier_call_graph_summary reducer"
    )
    requested_classifier_id = classifier_id
    if not requested_classifier_id:
        raise ValueError("CLASSIFIER_CALL_GRAPH requires classifier_id.")
    resolved_classifier_id = queries.resolve_classifier_id(
        conn, snapshot_id, requested_classifier_id
    )
    artifact_available = artifact_db_available(repo_root) if repo_root else False

    limit = _normalize_top_k(top_k)
    resolved_caller_id = _resolve_optional_classifier_id(conn, snapshot_id, caller_id)
    resolved_callee_id = _resolve_optional_classifier_id(conn, snapshot_id, callee_id)

    outgoing_edges = load_class_call_edges(
        repo_root,
        src_class_ids=[resolved_classifier_id],
        dst_class_ids=[resolved_callee_id] if resolved_callee_id else None,
    )
    incoming_edges = load_class_call_edges(
        repo_root,
        src_class_ids=[resolved_caller_id] if resolved_caller_id else None,
        dst_class_ids=[resolved_classifier_id],
    )

    classifier_ids = {resolved_classifier_id}
    for src_id, dst_id, _count in outgoing_edges + incoming_edges:
        classifier_ids.add(src_id)
        classifier_ids.add(dst_id)
    name_lookup = _classifier_name_lookup(conn, snapshot_id, classifier_ids)

    outgoing_all = _edges_to_entries(
        outgoing_edges, direction="outgoing", name_lookup=name_lookup
    )
    incoming_all = _edges_to_entries(
        incoming_edges, direction="incoming", name_lookup=name_lookup
    )
    outgoing = _apply_top_k(outgoing_all, limit)
    incoming = _apply_top_k(incoming_all, limit)

    body = {
        "payload_kind": "summary",
        "classifier_id": name_lookup.get(resolved_classifier_id, requested_classifier_id),
        "classifier_structural_id": resolved_classifier_id,
        "caller_id": name_lookup.get(resolved_caller_id, caller_id) if resolved_caller_id else None,
        "callee_id": name_lookup.get(resolved_callee_id, callee_id) if resolved_callee_id else None,
        "outgoing_count": len(outgoing),
        "incoming_count": len(incoming),
        "outgoing_total": len(outgoing_all),
        "incoming_total": len(incoming_all),
        "outgoing_listed_count": len(outgoing),
        "incoming_listed_count": len(incoming),
        "outgoing_coverage_ratio": _coverage_ratio(len(outgoing), len(outgoing_all)),
        "incoming_coverage_ratio": _coverage_ratio(len(incoming), len(incoming_all)),
        "total_edges": len(outgoing_all) + len(incoming_all),
        "changed_edge_count": 0,
        "added_edge_count": 0,
        "removed_edge_count": 0,
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
    overlay = current_overlay_payload()
    if overlay is not None:
        body = patch_classifier_call_graph_summary(
            body,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
        body["_overlay_applied_by_reducer"] = True
    return render_json_payload(body)


def _resolve_optional_classifier_id(
    conn, snapshot_id: str, classifier_id: str | None
) -> str | None:
    if not classifier_id:
        return None
    return queries.resolve_classifier_id(conn, snapshot_id, classifier_id)


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
                "src_classifier_id": src_id,
                "dst_classifier_id": dst_id,
                "src_classifier_qualified_name": name_lookup.get(src_id),
                "dst_classifier_qualified_name": name_lookup.get(dst_id),
                "direction": direction,
                "call_count": count,
                "committed_call_count": count,
                "overlay_call_count": count,
                "delta_call_count": 0,
                "row_origin": "committed",
                "is_active": True,
            }
        )
    entries.sort(
        key=lambda item: (
            -int(item["call_count"]),
            str(item["src_classifier_id"]),
            str(item["dst_classifier_id"]),
        )
    )
    return entries


def _classifier_name_lookup(
    conn, snapshot_id: str, classifier_ids: set[str]
) -> Dict[str, str]:
    if not classifier_ids:
        return {}
    placeholders = ",".join("?" for _ in classifier_ids)
    rows = conn.execute(
        f"""
        SELECT ni.structural_id, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'classifier'
          AND ni.structural_id IN ({placeholders})
        """,
        (snapshot_id, *classifier_ids),
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
        raise ValueError("classifier_call_graph_summary top_k must be a positive integer.")
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
