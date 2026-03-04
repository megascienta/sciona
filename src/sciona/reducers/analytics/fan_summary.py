# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Fan-in/fan-out summary reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ...code_analysis.analysis.orderings import order_nodes
from ..helpers import queries
from ..helpers.artifact_graph_edges import artifact_db_available
from ..helpers.artifact_graph_rollups import load_node_fan_stats
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="fan_summary",
    category="analytics",
    scope="codebase",
    placeholders=("FAN_SUMMARY",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Fan-in/fan-out metrics for calls and imports. " \
    "Use to identify highly connected entities or hotspots. " \
    "Scope: callable/class/module. Payload kind: summary.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    class_id: str | None = None,
    module_id: str | None = None,
    top_k: int | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="fan_summary reducer"
    )
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    artifact_available = artifact_db_available(repo_root) if repo_root else False
    resolved_id = None
    if method_id:
        resolved_id = queries.resolve_method_id(conn, snapshot_id, method_id)
    elif function_id:
        resolved_id = queries.resolve_function_id(conn, snapshot_id, function_id)
    elif class_id:
        resolved_id = queries.resolve_class_id(conn, snapshot_id, class_id)
    elif module_id:
        resolved_id = _resolve_module_id(conn, snapshot_id, module_id)
    limit = _normalize_top_k(top_k, default=5)

    if resolved_id:
        stats = load_node_fan_stats(
            repo_root,
            node_ids=[resolved_id],
        )
        edge_map: Dict[str, Dict[str, int]] = {}
        for _node_id, _node_kind, edge_kind, fan_in, fan_out in stats:
            edge_map[edge_kind] = {"fan_in": fan_in, "fan_out": fan_out}
        body = {
            "payload_kind": "summary",
            "node_id": resolved_id,
            "edge_kinds": edge_map,
            "edge_summary": edge_map,
            "top_k": limit,
            "artifact_available": artifact_available,
            "edge_source": "artifact_db" if artifact_available else "none",
        }
        return render_json_payload(body)

    call_stats = load_node_fan_stats(
        repo_root,
        edge_kinds=["CALLS"],
        node_kinds=["callable"],
    )
    import_stats = load_node_fan_stats(
        repo_root,
        edge_kinds=["IMPORTS_DECLARED"],
        node_kinds=["module"],
    )
    calls_table = _fan_tables(conn, snapshot_id, call_stats, top_k=limit)
    imports_table = _fan_tables(conn, snapshot_id, import_stats, top_k=limit)
    body = {
        "payload_kind": "summary",
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
    return {
        "total": total,
        "top_k": top_k,
        "fan_in_coverage_ratio": _coverage_ratio(len(by_fan_in), total),
        "fan_out_coverage_ratio": _coverage_ratio(len(by_fan_out), total),
        "by_fan_in": _fan_entries(conn, snapshot_id, by_fan_in, index=3),
        "by_fan_out": _fan_entries(conn, snapshot_id, by_fan_out, index=4),
    }


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
