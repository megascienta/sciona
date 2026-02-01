"""Compressed confidence reducer."""
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
    reducer_id="confidence_summary",
    scope="codebase",
    placeholders=("CONFIDENCE_SUMMARY",),
    determinism="conditional",
    payload_size_stats=None,
    semantic_tag="evidence",
    summary="Confidence summary for classes, functions, methods, or codebase.",
    lossy=True,
)

def _confidence_payload(payload: dict) -> dict:
    confidence = payload.get("confidence") or {}
    exists_now = confidence.get("exists_now")
    score = None
    if exists_now is not None:
        score = 1.0 if exists_now else 0.0
    has_source = bool(payload.get("file_path") and payload.get("line_span"))
    has_signature = bool(payload.get("parameters") or payload.get("signature") or payload.get("methods"))
    return {
        "confidence": score,
        "has_source": has_source,
        "has_signature": has_signature,
    }

def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    class_id: str | None = None,
    scope: str | None = None,  # explicitly supported: {"codebase", None}
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="confidence_summary reducer")
    if scope not in {None, "codebase"}:
        raise ValueError("CONFIDENCE_SUMMARY: invalid scope.")
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    if scope == "codebase":
        payload = load_structural_index(snapshot_id, conn, repo_root)
        summary = payload.get("confidence_summary") or {}
        score = summary.get("average_confidence")
        body = {"coverage_confidence": score}
        return render_json_payload(body)
    if method_id:
        payload = load_method_overview(snapshot_id, conn, repo_root, method_id)
    elif function_id:
        payload = load_function_overview(snapshot_id, conn, repo_root, function_id)
    elif class_id:
        payload = load_class_overview(snapshot_id, conn, repo_root, class_id)
    else:
        raise ValueError("CONFIDENCE_SUMMARY requires function_id, method_id, or class_id.")
    body = _confidence_payload(payload)
    return render_json_payload(body)
