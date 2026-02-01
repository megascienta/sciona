"""Compressed module summary reducer."""
from __future__ import annotations

from ..metadata import ReducerMeta
from ..helpers.base import (
    load_class_overview,
    load_function_overview,
    load_method_overview,
    load_module_overview,
    render_json_payload,
    require_connection,
)
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="module_summary",
    scope="module",
    placeholders=("MODULE_SUMMARY",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="summary",
    summary="Compressed structural summary for a module.",
    lossy=True,
)

# NOTE:
# This reducer is intentionally compressed and orientation-only.
# Do NOT add prose, intent, continuity, file paths, or node IDs.
# It is shared by code assembly and synthesize_module.

def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    class_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="module_summary reducer")
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    if not module_id:
        if method_id:
            module_id = load_method_overview(snapshot_id, conn, repo_root, method_id).get("module_id")
        elif function_id:
            module_id = load_function_overview(snapshot_id, conn, repo_root, function_id).get("module_id")
        elif class_id:
            module_id = load_class_overview(snapshot_id, conn, repo_root, class_id).get("module_id")
    if not module_id:
        raise ValueError("MODULE_SUMMARY requires a resolvable module_id.")
    payload = load_module_overview(
        snapshot_id=snapshot_id,
        module_id=module_id,
        conn=conn,
        repo_root=repo_root,
    )

    files = payload.get("file_count", 0)
    node_counts = payload.get("node_counts", {}) or {}
    classes = node_counts.get("classes", 0)
    functions = node_counts.get("functions", 0)

    public_symbols: list[str] = []
    for entry in payload.get("classes", []) + payload.get("functions", []):
        if len(public_symbols) >= 10:
            break
        name = None
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("qualified_name")
        if name:
            name = name.split(".")[-1]
        if name and name not in public_symbols:
            public_symbols.append(name)

    imports: list[str] = []
    for imp in payload.get("imports", []):
        if len(imports) >= 10:
            break
        module_name = imp.get("module_id")
        if module_name and module_name not in imports:
            imports.append(module_name)

    body = {
        "module": module_id,
        "kind": "module",
        "files": files,
        "classes": classes,
        "functions": functions,
        "public_symbols": public_symbols,
        "imports": imports,
    }

    return render_json_payload(body)
