# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compressed hotspot summary reducer."""

from __future__ import annotations

from collections import Counter

from ..metadata import ReducerMeta
from ..helpers.base import load_structural_index
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot, top_modules

REDUCER_META = ReducerMeta(
    reducer_id="hotspot_summary",
    category="summary",
    scope="codebase",
    placeholders=("HOTSPOT_SUMMARY",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Compressed codebase hotspot summary.",
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
            (entry.get("class_count") or 0)
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

    fan_in = Counter()
    fan_out = Counter()
    for edge in edges:
        src = edge.get("from_module_qualified_name")
        dst = edge.get("to_module_qualified_name")
        if src:
            fan_out[src] += 1
        if dst:
            fan_in[dst] += 1

    by_fan_in = [
        {"module_qualified_name": name, "count": count}
        for name, count in top_modules(fan_in, limit=5)
    ]
    by_fan_out = [
        {"module_qualified_name": name, "count": count}
        for name, count in top_modules(fan_out, limit=5)
    ]

    body = {
        "by_size": by_size,
        "by_fan_in": by_fan_in,
        "by_fan_out": by_fan_out,
        "artifact_available": (payload.get("imports") or {}).get("artifact_available"),
        "edge_source": (payload.get("imports") or {}).get("edge_source"),
    }
    return render_json_payload(body)
