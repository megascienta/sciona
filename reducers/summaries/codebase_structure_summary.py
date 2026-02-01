"""Compressed codebase structure summary reducer."""
from __future__ import annotations

from collections import Counter

from ..metadata import ReducerMeta
from ..helpers.base import load_structural_index, render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="codebase_structure_summary",
    scope="codebase",
    placeholders=("CODEBASE_STRUCTURE_SUMMARY",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="summary",
    summary="Compressed codebase structural summary.",
    lossy=True,
)

def render(snapshot_id: str, conn, repo_root, **_: object) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="codebase_structure_summary reducer")
    payload = load_structural_index(snapshot_id, conn, repo_root)
    module_entries = (payload.get("modules") or {}).get("entries", []) or []

    pkg_counter = Counter()
    for entry in module_entries:
        name = entry.get("module_id")
        if not name:
            continue
        pkg_counter[name.split(".", 1)[0]] += 1
    size_counts = []
    for entry in module_entries:
        size_counts.append(
            (entry.get("class_count") or 0)
            + (entry.get("function_count") or 0)
            + (entry.get("method_count") or 0)
        )
    size_counts.sort()
    size_summary = _summarize_distribution(size_counts)

    body = {
        "module_size_distribution": size_summary,
        "frequent_namespaces": [pkg for pkg, _count in pkg_counter.most_common(5)],
    }
    return render_json_payload(body)

def _summarize_distribution(values: list[int]) -> dict:
    if not values:
        return {"min": None, "median": None, "max": None}
    mid = len(values) // 2
    if len(values) % 2 == 1:
        median = values[mid]
    else:
        median = int((values[mid - 1] + values[mid]) / 2)
    return {
        "min": values[0],
        "median": median,
        "max": values[-1],
    }
