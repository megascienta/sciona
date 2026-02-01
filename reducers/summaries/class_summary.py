"""Compressed class summary reducer."""
from __future__ import annotations

from ..metadata import ReducerMeta
from ..helpers.base import load_class_overview, load_method_overview, render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="class_summary",
    scope="class",
    placeholders=("CLASS_SUMMARY",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="summary",
    summary="Compressed structural summary for a class.",
    lossy=True,
)

def render(
    snapshot_id: str,
    conn,
    repo_root,
    class_id: str | None = None,
    method_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="class_summary reducer")
    if not class_id and method_id:
        method_payload = load_method_overview(snapshot_id, conn, repo_root, method_id)
        class_id = method_payload.get("parent_structural_id") or method_payload.get("parent_qualified_name")
    if not class_id:
        raise ValueError("CLASS_SUMMARY requires class_id.")
    payload = load_class_overview(snapshot_id, conn, repo_root, class_id)

    methods = []
    for entry in payload.get("methods", []) or []:
        name = entry.get("qualified_name") if isinstance(entry, dict) else None
        if not name:
            continue
        methods.append(name.split(".")[-1])

    public_methods = [name for name in methods if not name.startswith("_")][:10]
    private_methods = [name for name in methods if name.startswith("_")][:10]

    class_name = payload.get("name")
    if not class_name:
        class_name = (payload.get("class_id") or "").split(".")[-1] or None
    body = {
        "class": class_name,
        "module": payload.get("module_id") or None,
        "bases": payload.get("bases") or [],
        "methods": {
            "public": public_methods,
            "private": private_methods,
        },
    }
    return render_json_payload(body)
