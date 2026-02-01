"""Callable context bundle reducer."""
from __future__ import annotations

import json

from ..helpers.base import load_callable_overview
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta
from ..summaries import callsite_index, callable_summary, module_summary
from ..baseline import callable_source

REDUCER_META = ReducerMeta(
    reducer_id="callable_context_bundle",
    scope="function",
    placeholders=("CALLABLE_CONTEXT_BUNDLE",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="context",
    summary="Bundled callable context (summary, source, callsites, module summary).",
    lossy=True,
    composite=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    direction: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="callable_context_bundle reducer")
    if callable_id and (function_id or method_id):
        raise ValueError("callable_context_bundle expects only one of callable_id/function_id/method_id.")
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    overview = load_callable_overview(
        snapshot_id,
        conn,
        repo_root,
        function_id=function_id,
        method_id=method_id,
    )
    resolved_id = overview.get("function_id") or overview.get("method_id") or overview.get("requested_identifier")
    module_id = overview.get("module_id")
    summary_payload = _parse_json_fence(
        callable_summary.render(
            snapshot_id,
            conn,
            repo_root,
            function_id=function_id,
            method_id=method_id,
        )
    )
    source_payload = _parse_json_fence(
        callable_source.render(
            snapshot_id,
            conn,
            repo_root,
            callable_id=callable_id,
            function_id=function_id,
            method_id=method_id,
        )
    )
    callsite_payload = _parse_json_fence(
        callsite_index.render(
            snapshot_id,
            conn,
            repo_root,
            function_id=function_id,
            method_id=method_id,
            direction=direction,
        )
    )
    module_payload = None
    if module_id:
        module_payload = _parse_json_fence(
            module_summary.render(
                snapshot_id,
                conn,
                repo_root,
                module_id=module_id,
            )
        )
    body = {
        "callable_id": resolved_id,
        "module_id": module_id,
        "callable_summary": summary_payload,
        "callable_source": source_payload,
        "callsite_index": callsite_payload,
        "module_summary": module_payload,
    }
    return render_json_payload(body)


def _parse_json_fence(text: str) -> object:
    trimmed = text.strip()
    if trimmed.startswith("```json") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        trimmed = "\n".join(lines[1:-1])
    return json.loads(trimmed)
