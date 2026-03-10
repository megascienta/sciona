# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callsite index reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ....pipelines.diff_overlay.patchers.analytics import patch_callsite_index
from ..shared import queries
from ..artifact_call_sites import load_callsite_enrichment
from ..artifact_graph_edges import (
    artifact_db_available,
    load_artifact_edges,
)
from ..shared.context import current_overlay_payload
from ..shared.render import render_json_payload, require_connection
from ..shared.utils import require_latest_committed_snapshot
from ...metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="callsite_index",
    category="relations",
    risk_tier="normal",
    stage="relationship_analysis",
    placeholder="CALLSITE_INDEX",
    summary="List artifact-layer callsite resolution outcomes for a callable, with "
    "optional narrowing by identifier, resolution status, provenance, or drop "
    "reason. detail_level='neighbors' returns caller/callee sets. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    direction: str | None = None,
    detail_level: str | None = None,
    include_callsite_diagnostics: bool | None = None,
    identifier: str | None = None,
    status: str | None = None,
    provenance: str | None = None,
    drop_reason: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="callsite_index reducer"
    )
    resolved_id = _resolve_callable_id(
        conn,
        snapshot_id,
        callable_id=callable_id,
    )
    level = _normalize_detail_level(detail_level)
    if level == "neighbors":
        body = build_neighbors_payload(conn, snapshot_id, repo_root, resolved_id)
        return render_json_payload(body)
    dir_value = _normalize_direction(direction)
    status_value = _normalize_status(status)
    provenance_value = _normalize_provenance(provenance)
    drop_reason_value = _normalize_drop_reason(drop_reason)
    filter_active = any(
        value is not None
        for value in (identifier, status_value, provenance_value, drop_reason_value)
    )
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
                "row_origin": "committed",
                "transition": "unchanged",
            }
        )
    body = {
        "payload_kind": "summary",
        "callable_id": resolved_id,
        "call_sites_semantics": "filtered_persisted_artifact_working_set",
        "external_likely_semantics": "residual_filter_quality_signal",
        "direction": dir_value,
        "detail_level": level,
        "filters": {
            "identifier": identifier,
            "status": status_value,
            "provenance": provenance_value,
            "drop_reason": drop_reason_value,
        },
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
        "edge_count": len(enriched),
        "edges": enriched,
        "edge_transition_summary": {
            "unchanged": len(enriched),
            "accepted_to_dropped": 0,
            "dropped_to_accepted": 0,
            "provenance_changed": 0,
        },
        "call_sites": [],
        "resolution_diagnostics": {},
    }
    should_load_callsites = artifact_available and repo_root is not None and (
        bool(include_callsite_diagnostics) or filter_active
    )
    if should_load_callsites:
        call_sites, diagnostics = load_callsite_enrichment(
            repo_root=repo_root,
            snapshot_id=snapshot_id,
            caller_id=resolved_id,
        )
        filtered_call_sites = _filter_call_sites(
            call_sites,
            identifier=identifier,
            status=status_value,
            provenance=provenance_value,
            drop_reason=drop_reason_value,
        )
        body["call_sites"] = [
            {
                "identifier": row.get("identifier"),
                "resolution_status": row.get("resolution_status"),
                "accepted_callee_id": row.get("accepted_callee_id"),
                "provenance": row.get("provenance"),
                "drop_reason": row.get("drop_reason"),
                "candidate_count": row.get("candidate_count"),
                "callee_kind": row.get("callee_kind"),
                "line_span": (
                    [row.get("call_start_byte"), row.get("call_end_byte")]
                    if row.get("call_start_byte") is not None
                    and row.get("call_end_byte") is not None
                    else None
                ),
                "ordinal": row.get("call_ordinal"),
                "row_origin": "committed",
                "transition": "unchanged",
            }
            for row in filtered_call_sites
        ]
        body["resolution_diagnostics"] = diagnostics
        if filter_active:
            allowed_callees = {
                str(row.get("accepted_callee_id"))
                for row in filtered_call_sites
                if row.get("accepted_callee_id")
            }
            body["edges"] = _filter_edges_by_callees(
                enriched,
                allowed_callees=allowed_callees,
                status=status_value,
            )
            body["edge_count"] = len(body["edges"])
    overlay = current_overlay_payload()
    if overlay is not None:
        body = patch_callsite_index(
            body,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
        body["_overlay_applied_by_reducer"] = True
    return render_json_payload(body)


def build_neighbors_payload(conn, snapshot_id: str, repo_root, resolved_id: str) -> dict:
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
    return {
        "payload_kind": "summary",
        "callable_id": resolved_id,
        "caller_count": len(callers),
        "callee_count": len(callees),
        "callers": callers,
        "callees": callees,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }


def _resolve_callable_id(
    conn,
    snapshot_id: str,
    *,
    callable_id: str | None,
) -> str:
    return queries.resolve_callable_id(conn, snapshot_id, callable_id)


def _normalize_detail_level(detail_level: Optional[str]) -> str:
    if not detail_level:
        return "callsites"
    value = str(detail_level).strip().lower()
    if value in {"callsites", "neighbors"}:
        return value
    raise ValueError("callsite_index detail_level must be 'callsites' or 'neighbors'.")


def _normalize_direction(direction: Optional[str]) -> str:
    if not direction:
        return "both"
    value = str(direction).strip().lower()
    if value in {"in", "out", "both"}:
        return value
    raise ValueError("callsite_index direction must be one of: in, out, both.")


def _normalize_status(status: Optional[str]) -> str | None:
    if status is None:
        return None
    value = str(status).strip().lower()
    if value in {"accepted", "dropped"}:
        return value
    raise ValueError("callsite_index status must be one of: accepted, dropped.")


def _normalize_provenance(provenance: Optional[str]) -> str | None:
    if provenance is None:
        return None
    value = str(provenance).strip()
    if value in {
        "exact_qname",
        "module_scoped",
        "import_narrowed",
        "export_chain_narrowed",
    }:
        return value
    raise ValueError(
        "callsite_index provenance must be one of: exact_qname, module_scoped, "
        "import_narrowed, export_chain_narrowed."
    )


def _normalize_drop_reason(drop_reason: Optional[str]) -> str | None:
    if drop_reason is None:
        return None
    value = str(drop_reason).strip()
    if value in {
        "no_candidates",
        "unique_without_provenance",
        "ambiguous_no_caller_module",
        "ambiguous_no_in_scope_candidate",
        "ambiguous_multiple_in_scope_candidates",
    }:
        return value
    raise ValueError(
        "callsite_index drop_reason must be one of: no_candidates, "
        "unique_without_provenance, ambiguous_no_caller_module, "
        "ambiguous_no_in_scope_candidate, ambiguous_multiple_in_scope_candidates."
    )


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
    edges.sort(
        key=lambda entry: (
            str(entry.get("caller_id")),
            str(entry.get("callee_id")),
            str(entry.get("edge_kind")),
        )
    )
    return edges


def _filter_call_sites(
    call_sites: List[Dict[str, object]],
    *,
    identifier: str | None,
    status: str | None,
    provenance: str | None,
    drop_reason: str | None,
) -> List[Dict[str, object]]:
    filtered: List[Dict[str, object]] = []
    for row in call_sites:
        if identifier is not None and row.get("identifier") != identifier:
            continue
        if status is not None and row.get("resolution_status") != status:
            continue
        if provenance is not None and row.get("provenance") != provenance:
            continue
        if drop_reason is not None and row.get("drop_reason") != drop_reason:
            continue
        filtered.append(row)
    return filtered


def _filter_edges_by_callees(
    edges: List[Dict[str, object]],
    *,
    allowed_callees: set[str],
    status: str | None,
) -> List[Dict[str, object]]:
    if status == "dropped":
        return []
    if not allowed_callees:
        return []
    return [
        edge
        for edge in edges
        if str(edge.get("callee_id") or "") in allowed_callees
    ]


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
    entries = [
        {
            "structural_id": row["structural_id"],
            "qualified_name": row["qualified_name"],
            "node_type": row["node_type"],
        }
        for row in rows
        if row["qualified_name"]
    ]
    entries.sort(key=lambda item: (str(item.get("qualified_name")), str(item.get("structural_id"))))
    return entries
