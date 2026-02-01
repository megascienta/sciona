"""Compressed callable summary reducer."""
from __future__ import annotations

from ..metadata import ReducerMeta
from ..helpers.base import load_callable_overview, render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="callable_summary",
    scope="function",
    placeholders=("CALLABLE_SUMMARY",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="summary",
    summary="Compressed structural summary for a callable (function or method).",
    lossy=True,
)

def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="callable_summary reducer")
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    payload = load_callable_overview(
        snapshot_id,
        conn,
        repo_root,
        function_id=function_id,
        method_id=method_id,
    )

    requested = payload.get("requested_identifier") or payload.get("function_id") or ""
    name = requested.split(".")[-1] if requested else ""
    signature = payload.get("signature") or ""
    if signature:
        name = signature.split("(", 1)[0]

    body = {
        "name": name or None,
        "kind": "callable",
        "module": payload.get("module_id") or None,
        "parameters": payload.get("parameters") or [],
        "returns": None,
        "calls": None,
        "raises": None,
    }
    return render_json_payload(body)
