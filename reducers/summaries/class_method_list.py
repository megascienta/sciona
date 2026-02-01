"""Class method list reducer."""
from __future__ import annotations

from ..metadata import ReducerMeta
from ..helpers.base import load_class_overview, render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="class_method_list",
    scope="class",
    placeholders=("CLASS_METHOD_LIST",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="context",
    summary="List of methods for a class with basic visibility.",
    lossy=True,
)

def render(
    snapshot_id: str,
    conn,
    repo_root,
    class_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="class_method_list reducer")
    if not class_id:
        raise ValueError("CLASS_METHOD_LIST requires class_id.")
    payload = load_class_overview(snapshot_id, conn, repo_root, class_id)
    methods = []
    for entry in payload.get("methods") or []:
        name = entry.get("qualified_name") if isinstance(entry, dict) else None
        if not name:
            continue
        short = name.split(".")[-1]
        visibility = "private" if short.startswith("_") else "public"
        methods.append({"name": short, "visibility": visibility})
        if len(methods) >= 25:
            break
    return render_json_payload({"methods": methods})
