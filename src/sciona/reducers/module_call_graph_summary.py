# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Module-level call graph reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..runtime.overlay.patching.analytics import patch_module_call_graph_summary
from .helpers.shared import queries
from .helpers.artifact.graph_edges import artifact_db_available
from .helpers.artifact.graph_rollups import load_module_call_edges
from .helpers.shared.context import current_overlay_payload
from .helpers.shared.render import render_json_payload, require_connection
from .helpers.shared.utils import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="module_call_graph_summary",
    category="coupling",
    placeholder="MODULE_CALL_GRAPH",
    summary="Summarize module-to-module artifact call relationships for the committed "
    "snapshot, with optional narrowing by caller or callee module. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    callable_id: str | None = None,
    classifier_id: str | None = None,
    from_module_id: str | None = None,
    to_module_id: str | None = None,
    compact: bool | None = None,
    top_k: int | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="module_call_graph_summary reducer"
    )
    resolved_module_name = module_id
    if not resolved_module_name and classifier_id:
        classifier_structural_id = queries.resolve_classifier_id(
            conn, snapshot_id, classifier_id
        )
        resolved_module_name = queries.module_id_for_structural(
            conn, snapshot_id, classifier_structural_id
        )
    if not resolved_module_name and callable_id:
        callable_structural_id = queries.resolve_callable_id(
            conn, snapshot_id, callable_id
        )
        resolved_module_name = queries.module_id_for_structural(
            conn, snapshot_id, callable_structural_id
        )
    if not resolved_module_name:
        raise ValueError("MODULE_CALL_GRAPH requires a resolvable module_id.")
    module_name_lookup = _module_name_lookup(conn, snapshot_id)
    resolved_module_structural_id, resolved_module_name = _resolve_required_module(
        conn, snapshot_id, resolved_module_name
    )
    artifact_available = artifact_db_available(repo_root) if repo_root else False

    limit = _normalize_top_k(top_k)
    resolved_from_module_structural_id, resolved_from_module_name = _resolve_optional_module(
        conn, snapshot_id, from_module_id
    )
    resolved_to_module_structural_id, resolved_to_module_name = _resolve_optional_module(
        conn, snapshot_id, to_module_id
    )

    outgoing_edges = load_module_call_edges(
        repo_root,
        src_module_ids=[resolved_module_structural_id],
        dst_module_ids=[resolved_to_module_structural_id]
        if resolved_to_module_structural_id
        else None,
    )
    incoming_edges = load_module_call_edges(
        repo_root,
        src_module_ids=[resolved_from_module_structural_id]
        if resolved_from_module_structural_id
        else None,
        dst_module_ids=[resolved_module_structural_id],
    )

    outgoing_all = _edges_to_entries(
        outgoing_edges, direction="outgoing", name_lookup=module_name_lookup
    )
    incoming_all = _edges_to_entries(
        incoming_edges, direction="incoming", name_lookup=module_name_lookup
    )
    outgoing = _apply_top_k(outgoing_all, limit)
    incoming = _apply_top_k(incoming_all, limit)

    body = {
        "payload_kind": "summary",
        "module_qualified_name": resolved_module_name,
        "module_structural_id": resolved_module_structural_id,
        "from_module_id": resolved_from_module_name,
        "to_module_id": resolved_to_module_name,
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
        body = patch_module_call_graph_summary(
            body,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
        body["_overlay_applied_by_reducer"] = True
    if compact:
        body = _compact_payload(body, preview_limit=limit)
    return render_json_payload(body)


def _module_name_lookup(conn, snapshot_id: str) -> Dict[str, str]:
    rows = queries.list_modules(conn, snapshot_id)
    return {
        str(row["structural_id"]): str(row["qualified_name"])
        for row in rows
        if row.get("structural_id") and row.get("qualified_name")
    }


def _resolve_required_module(conn, snapshot_id: str, module_id: str) -> tuple[str, str]:
    structural_id, qualified_name = _resolve_optional_module(conn, snapshot_id, module_id)
    if not structural_id or not qualified_name:
        raise ValueError(f"Module '{module_id}' not found in snapshot '{snapshot_id}'.")
    return structural_id, qualified_name


def _resolve_optional_module(
    conn, snapshot_id: str, module_id: str | None
) -> tuple[str | None, str | None]:
    if not module_id:
        return None, None
    rows = queries.list_modules(conn, snapshot_id)
    for row in rows:
        structural_id = row.get("structural_id")
        qualified_name = row.get("qualified_name")
        if module_id == structural_id or module_id == qualified_name:
            return str(structural_id), str(qualified_name)
    raise ValueError(f"Module '{module_id}' not found in snapshot '{snapshot_id}'.")


def _edges_to_entries(
    edges: List[tuple[str, str, int]], *, direction: str, name_lookup: Dict[str, str]
) -> List[Dict[str, int | str]]:
    entries: List[Dict[str, int | str]] = []
    for src_id, dst_id, count in edges:
        entries.append(
            {
                "src_module_structural_id": src_id,
                "dst_module_structural_id": dst_id,
                "src_module_qualified_name": name_lookup.get(src_id, src_id),
                "dst_module_qualified_name": name_lookup.get(dst_id, dst_id),
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


def _compact_payload(
    payload: Dict[str, object], *, preview_limit: Optional[int]
) -> Dict[str, object]:
    limit = preview_limit or 10
    outgoing_all = list(payload.get("outgoing", []) or [])
    incoming_all = list(payload.get("incoming", []) or [])
    compact_payload = dict(payload)
    compact_payload["payload_kind"] = "compact_summary"
    compact_payload["preview_limit"] = limit
    compact_payload["outgoing_preview"] = _preview_block(outgoing_all, limit)
    compact_payload["incoming_preview"] = _preview_block(incoming_all, limit)
    compact_payload.pop("outgoing", None)
    compact_payload.pop("incoming", None)
    return compact_payload


def _preview_block(entries: List[Dict[str, int | str]], limit: int) -> Dict[str, object]:
    shown = entries[:limit]
    return {
        "count": len(shown),
        "total": len(entries),
        "truncated": len(entries) > limit,
        "entries": shown,
    }
