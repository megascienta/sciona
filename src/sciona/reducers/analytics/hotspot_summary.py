# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compressed hotspot summary reducer."""

from __future__ import annotations

from collections import Counter

from ..metadata import ReducerMeta
from ..helpers.base import load_structural_index
from ..helpers.artifact_graph_rollups import load_node_fan_stats
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot, top_modules

REDUCER_META = ReducerMeta(
    reducer_id="hotspot_summary",
    category="analytics",
    scope="codebase",
    placeholders=("HOTSPOT_SUMMARY",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Compressed summary of structurally significant or highly connected entities. " \
    "Use for architectural orientation or complexity inspection. " \
    "Scope: codebase-level. Payload kind: summary.",
    lossy=True,
)


def render(snapshot_id: str, conn, repo_root, **_: object) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="hotspot_summary reducer"
    )
    payload = load_structural_index(snapshot_id, conn, repo_root)
    module_entries = (payload.get("modules") or {}).get("entries", []) or []
    edges = (payload.get("imports") or {}).get("edges", []) or []

    def _size_metric(entry: dict) -> int:
        return (
            (entry.get("classifier_count") or 0)
            + (entry.get("function_count") or 0)
            + (entry.get("method_count") or 0)
        )

    by_size = [
        {
            "module_qualified_name": entry.get("module_qualified_name"),
            "count": _size_metric(entry),
        }
        for entry in sorted(
            module_entries,
            key=lambda item: (
                -_size_metric(item),
                item.get("module_qualified_name") or "",
            ),
        )[:5]
        if entry.get("module_qualified_name")
    ]

    import_fan_in = Counter()
    import_fan_out = Counter()
    for edge in edges:
        src = edge.get("from_module_qualified_name")
        dst = edge.get("to_module_qualified_name")
        if src:
            import_fan_out[src] += 1
        if dst:
            import_fan_in[dst] += 1

    by_fan_in = [
        {"module_qualified_name": name, "count": count}
        for name, count in top_modules(import_fan_in, limit=5)
    ]
    by_fan_out = [
        {"module_qualified_name": name, "count": count}
        for name, count in top_modules(import_fan_out, limit=5)
    ]
    module_name_by_id = _module_name_lookup(conn, snapshot_id)
    rollup_rows = load_node_fan_stats(
        repo_root,
        node_ids=sorted(module_name_by_id.keys()),
        node_kinds=["module"],
        edge_kinds=["CALLS", "IMPORTS_DECLARED"],
    )
    by_call_fan_in, by_call_fan_out = _fan_rankings(
        rollup_rows,
        module_name_by_id,
        edge_kind="CALLS",
        limit=5,
    )
    by_import_fan_in, by_import_fan_out = _fan_rankings(
        rollup_rows,
        module_name_by_id,
        edge_kind="IMPORTS_DECLARED",
        limit=5,
    )

    body = {
        "payload_kind": "summary",
        "version": 2,
        "by_size": by_size,
        "by_fan_in": by_fan_in,
        "by_fan_out": by_fan_out,
        "by_call_fan_in": by_call_fan_in,
        "by_call_fan_out": by_call_fan_out,
        "by_import_fan_in": by_import_fan_in,
        "by_import_fan_out": by_import_fan_out,
        "artifact_available": (payload.get("imports") or {}).get("artifact_available"),
        "edge_source": (payload.get("imports") or {}).get("edge_source"),
    }
    return render_json_payload(body)


def _module_name_lookup(conn, snapshot_id: str) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT sn.structural_id, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni
          ON ni.structural_id = sn.structural_id
         AND ni.snapshot_id = ?
        WHERE sn.node_type = 'module'
        """,
        (snapshot_id,),
    ).fetchall()
    return {
        row["structural_id"]: row["qualified_name"]
        for row in rows
        if row["qualified_name"]
    }


def _fan_rankings(
    stats: list[tuple[str, str, str, int, int]],
    module_name_by_id: dict[str, str],
    *,
    edge_kind: str,
    limit: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    selected = [row for row in stats if row[2] == edge_kind]
    by_fan_in = sorted(selected, key=lambda row: (-row[3], module_name_by_id.get(row[0], row[0])))
    by_fan_out = sorted(selected, key=lambda row: (-row[4], module_name_by_id.get(row[0], row[0])))
    return (
        [
            {
                "module_id": row[0],
                "module_qualified_name": module_name_by_id.get(row[0]),
                "count": row[3],
            }
            for row in by_fan_in[:limit]
        ],
        [
            {
                "module_id": row[0],
                "module_qualified_name": module_name_by_id.get(row[0]),
                "count": row[4],
            }
            for row in by_fan_out[:limit]
        ],
    )
