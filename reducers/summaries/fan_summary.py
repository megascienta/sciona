"""Fan-in/fan-out summary reducer."""
from __future__ import annotations

from typing import Dict, List, Optional

from ...code_analysis.analysis.orderings import order_nodes
from ..helpers import queries
from ..helpers.artifact_graph_rollups import load_node_fan_stats
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="fan_summary",
    scope="codebase",
    placeholders=("FAN_SUMMARY",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="dependency",
    summary="Fan-in/out summary for calls and imports.",
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
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="fan_summary reducer")
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    resolved_id = None
    if method_id:
        resolved_id = queries.resolve_method_id(conn, snapshot_id, method_id)
    elif function_id:
        resolved_id = queries.resolve_function_id(conn, snapshot_id, function_id)
    elif class_id:
        resolved_id = queries.resolve_class_id(conn, snapshot_id, class_id)
    elif module_id:
        resolved_id = _resolve_module_id(conn, snapshot_id, module_id)
    if resolved_id:
        stats = load_node_fan_stats(
            repo_root,
            snapshot_id=snapshot_id,
            node_ids=[resolved_id],
        )
        edge_map: Dict[str, Dict[str, int]] = {}
        for _node_id, _node_kind, edge_kind, fan_in, fan_out in stats:
            edge_map[edge_kind] = {"fan_in": fan_in, "fan_out": fan_out}
        body = {
            "node_id": resolved_id,
            "edge_kinds": edge_map,
        }
        return render_json_payload(body)

    call_stats = load_node_fan_stats(
        repo_root,
        snapshot_id=snapshot_id,
        edge_kinds=["CALLS"],
        node_kinds=["function", "method"],
    )
    import_stats = load_node_fan_stats(
        repo_root,
        snapshot_id=snapshot_id,
        edge_kinds=["IMPORTS_DECLARED"],
        node_kinds=["module"],
    )
    body = {
        "calls": _fan_tables(conn, snapshot_id, call_stats),
        "imports": _fan_tables(conn, snapshot_id, import_stats),
    }
    return render_json_payload(body)


def _fan_tables(conn, snapshot_id: str, stats: List[tuple[str, str, str, int, int]]) -> Dict[str, List[Dict[str, int | str]]]:
    by_fan_in = sorted(stats, key=lambda item: (-item[3], item[0]))[:5]
    by_fan_out = sorted(stats, key=lambda item: (-item[4], item[0]))[:5]
    return {
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
    return {row["structural_id"]: row["qualified_name"] for row in rows if row["qualified_name"]}


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
        raise ValueError(f"Module '{identifier}' not found in snapshot '{snapshot_id}'.")
    return row["structural_id"]
