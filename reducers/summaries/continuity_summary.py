"""Continuity reducer."""
from __future__ import annotations

from ..metadata import ReducerMeta
from ..helpers.base import (
    load_class_overview,
    load_function_overview,
    load_method_overview,
    load_structural_index,
    render_json_payload,
    require_connection,
)
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="continuity_summary",
    scope="codebase",
    placeholders=("CONTINUITY_SUMMARY",),
    determinism="conditional",
    payload_size_stats=None,
    semantic_tag="evidence",
    summary="Continuity summary for codebase or node.",
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
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="continuity_summary reducer")
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    if class_id:
        payload = load_class_overview(snapshot_id, conn, repo_root, class_id)
        continuity = payload.get("confidence")
    elif method_id:
        payload = load_method_overview(snapshot_id, conn, repo_root, method_id)
        continuity = payload.get("confidence")
    elif function_id:
        payload = load_function_overview(snapshot_id, conn, repo_root, function_id)
        continuity = payload.get("confidence")
    else:
        payload = load_structural_index(snapshot_id, conn, repo_root)
        continuity = payload.get("confidence_summary")
    return render_json_payload({"continuity": continuity})
