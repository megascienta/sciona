# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Fan-in/fan-out summary reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..code_analysis.analysis.orderings import order_nodes
from ..pipelines.diff_overlay.patchers.analytics import patch_fan_summary
from .helpers.shared import queries
from .helpers.artifact.graph_edges import artifact_db_available
from .helpers.artifact.graph_rollups import load_node_fan_stats
from .helpers.shared.context import current_overlay_payload
from .helpers.shared.render import render_json_payload, require_connection
from .helpers.shared.utils import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="fan_summary",
    category="metrics",
    risk_tier="normal",
    stage="diagnostics_metrics",
    placeholder="FAN_SUMMARY",
    summary="Summarize fan-in and fan-out over reducer-facing graph edges, with "
    "optional narrowing by edge kind, node kind, and minimum fan threshold. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    classifier_id: str | None = None,
    module_id: str | None = None,
    edge_kind: str | None = None,
    min_fan: int | None = None,
    node_kind: str | None = None,
    top_k: int | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="fan_summary reducer"
    )
    artifact_available = artifact_db_available(repo_root) if repo_root else False
    edge_kind_value = _normalize_edge_kind(edge_kind)
    min_fan_value = _normalize_min_fan(min_fan)
    node_kind_value = _normalize_node_kind(node_kind)
    resolved_id = None
    if callable_id:
        resolved_id = queries.resolve_callable_id(conn, snapshot_id, callable_id)
    elif classifier_id:
        resolved_id = queries.resolve_classifier_id(conn, snapshot_id, classifier_id)
    elif module_id:
        resolved_id = _resolve_module_id(conn, snapshot_id, module_id)
    limit = _normalize_top_k(top_k, default=5)

    if resolved_id:
        stats = load_node_fan_stats(
            repo_root,
            node_ids=[resolved_id],
            edge_kinds=[edge_kind_value] if edge_kind_value else None,
        )
        edge_map: Dict[str, Dict[str, int]] = {}
        for _node_id, _node_kind, edge_kind, fan_in, fan_out in stats:
            edge_map[edge_kind] = {"fan_in": fan_in, "fan_out": fan_out}
        body = {
            "payload_kind": "summary",
            "node_id": resolved_id,
            "edge_kinds": {
                edge_name: {
                    **values,
                    "committed_fan_in": values.get("fan_in", 0),
                    "committed_fan_out": values.get("fan_out", 0),
                    "delta_fan_in": 0,
                    "delta_fan_out": 0,
                }
                for edge_name, values in edge_map.items()
            },
            "edge_summary": edge_map,
            "filters": {
                "edge_kind": edge_kind_value,
                "min_fan": min_fan_value,
                "node_kind": node_kind_value,
            },
            "top_k": limit,
            "artifact_available": artifact_available,
            "edge_source": "artifact_db" if artifact_available else "none",
        }
        overlay = current_overlay_payload()
        if overlay is not None:
            body = patch_fan_summary(
                body,
                overlay,
                snapshot_id=snapshot_id,
                conn=conn,
            )
            body["_overlay_applied_by_reducer"] = True
        return render_json_payload(body)

    call_stats = (
        load_node_fan_stats(
            repo_root,
            edge_kinds=["CALLS"] if edge_kind_value in {None, "CALLS"} else [],
            node_kinds=[node_kind_value] if node_kind_value else ["callable"],
        )
        if edge_kind_value in {None, "CALLS"}
        else []
    )
    import_stats = (
        load_node_fan_stats(
            repo_root,
            edge_kinds=["IMPORTS_DECLARED"]
            if edge_kind_value in {None, "IMPORTS_DECLARED"}
            else [],
            node_kinds=[node_kind_value] if node_kind_value else ["module"],
        )
        if edge_kind_value in {None, "IMPORTS_DECLARED"}
        else []
    )
    call_stats = _filter_min_fan(call_stats, min_fan_value)
    import_stats = _filter_min_fan(import_stats, min_fan_value)
    calls_table = _fan_tables(conn, snapshot_id, call_stats, top_k=limit)
    imports_table = _fan_tables(conn, snapshot_id, import_stats, top_k=limit)
    body = {
        "payload_kind": "summary",
        "filters": {
            "edge_kind": edge_kind_value,
            "min_fan": min_fan_value,
            "node_kind": node_kind_value,
        },
        "calls": calls_table,
        "imports": imports_table,
        "edge_summary": {
            "CALLS": {"rows": len(call_stats)},
            "IMPORTS_DECLARED": {"rows": len(import_stats)},
        },
        "top_k": limit,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }
    overlay = current_overlay_payload()
    if overlay is not None:
        body = patch_fan_summary(
            body,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
        body["_overlay_applied_by_reducer"] = True
    return render_json_payload(body)


def _fan_tables(
    conn,
    snapshot_id: str,
    stats: List[tuple[str, str, str, int, int]],
    *,
    top_k: Optional[int],
) -> Dict[str, object]:
    by_fan_in = sorted(stats, key=lambda item: (-item[3], item[0]))
    by_fan_out = sorted(stats, key=lambda item: (-item[4], item[0]))
    by_fan_in = _apply_top_k(by_fan_in, top_k)
    by_fan_out = _apply_top_k(by_fan_out, top_k)
    total = len(stats)
    table = {
        "total": total,
        "committed_total": total,
        "adjusted_total": total,
        "delta_total": 0,
        "top_k": top_k,
        "fan_in_coverage_ratio": _coverage_ratio(len(by_fan_in), total),
        "fan_out_coverage_ratio": _coverage_ratio(len(by_fan_out), total),
        "by_fan_in": _fan_entries(conn, snapshot_id, by_fan_in, index=3),
        "by_fan_out": _fan_entries(conn, snapshot_id, by_fan_out, index=4),
    }
    return table


def _fan_entries(
    conn,
    snapshot_id: str,
    stats: List[tuple[str, str, str, int, int]],
    *,
    index: int,
) -> List[Dict[str, int | str]]:
    node_ids = [row[0] for row in stats]
    name_lookup = _fetch_names(conn, snapshot_id, node_ids)
    entries = []
    for node_id, _node_kind, _edge_kind, fan_in, fan_out in stats:
        count = fan_in if index == 3 else fan_out
        entries.append(
            {
                "node_id": node_id,
                "qualified_name": name_lookup.get(node_id),
                "count": count,
                "committed_count": count,
                "adjusted_count": count,
                "delta_count": 0,
            }
        )
    order_nodes(entries, key=lambda item: (-int(item["count"]), str(item["node_id"])))
    return entries


def _fetch_names(conn, snapshot_id: str, node_ids: List[str]) -> Dict[str, str]:
    if not node_ids:
        return {}
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"""
        SELECT structural_id, qualified_name
        FROM node_instances
        WHERE snapshot_id = ?
          AND structural_id IN ({placeholders})
        """,
        (snapshot_id, *node_ids),
    ).fetchall()
    return {
        row["structural_id"]: row["qualified_name"]
        for row in rows
        if row["qualified_name"]
    }


def _resolve_module_id(conn, snapshot_id: str, identifier: str) -> Optional[str]:
    row = conn.execute(
        """
        SELECT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (sn.structural_id = ? OR ni.qualified_name = ?)
        LIMIT 1
        """,
        (snapshot_id, identifier, identifier),
    ).fetchone()
    if not row:
        raise ValueError(
            f"Module '{identifier}' not found in snapshot '{snapshot_id}'."
        )
    return row["structural_id"]


def _normalize_top_k(value: Optional[int], *, default: int) -> Optional[int]:
    if value is None:
        return default
    value = int(value)
    if value <= 0:
        raise ValueError("fan_summary top_k must be a positive integer.")
    return value


def _normalize_edge_kind(value: Optional[str]) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if normalized in {"CALLS", "IMPORTS_DECLARED"}:
        return normalized
    raise ValueError("fan_summary edge_kind must be one of: CALLS, IMPORTS_DECLARED.")


def _normalize_min_fan(value: Optional[int]) -> int | None:
    if value is None:
        return None
    normalized = int(value)
    if normalized < 0:
        raise ValueError("fan_summary min_fan must be zero or a positive integer.")
    return normalized


def _normalize_node_kind(value: Optional[str]) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"module", "classifier", "callable"}:
        return normalized
    raise ValueError("fan_summary node_kind must be one of: module, classifier, callable.")


def _filter_min_fan(
    stats: List[tuple[str, str, str, int, int]], min_fan: int | None
) -> List[tuple[str, str, str, int, int]]:
    if min_fan is None:
        return stats
    return [
        row
        for row in stats
        if max(int(row[3]), int(row[4])) >= min_fan
    ]


def _apply_top_k(
    stats: List[tuple[str, str, str, int, int]], top_k: Optional[int]
) -> List[tuple[str, str, str, int, int]]:
    if top_k is None:
        return stats
    return stats[:top_k]


def _coverage_ratio(selected: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return round(selected / total, 4)
