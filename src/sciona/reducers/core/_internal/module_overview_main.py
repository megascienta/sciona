# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Module overview reducer."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ....code_analysis.analysis.orderings import order_nodes, order_strings
from ...helpers import queries
from ...helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ...helpers.profile_utils import fetch_node_instance
from ...helpers.render import render_json_payload, require_connection
from ...helpers.types import ModuleOverviewPayload
from ...helpers.utils import line_span_hash, require_latest_committed_snapshot
from ...metadata import ReducerMeta
from .module_overview_relations import (
    _language_breakdown,
    _list_children,
    _list_imports,
    _list_methods,
    _list_nested_classes,
)
from .module_overview_resolve import (
    _list_module_files,
    _module_file_entries,
    _resolve_module,
    _resolve_module_ids,
)

REDUCER_META = ReducerMeta(
    reducer_id="module_overview",
    category="core",
    scope="module",
    placeholders=("MODULE_OVERVIEW",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Structural summary of a module, including contained classes and callables. " \
    "Use for architectural inspection. " \
    "Scope: module-level. Payload kind: summary.",
)

def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    class_id: str | None = None,
    include_file_map: bool | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    resolved_module_id = module_id
    if not resolved_module_id and class_id:
        class_structural_id = queries.resolve_class_id(conn, snapshot_id, class_id)
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, class_structural_id
        )
    if not resolved_module_id and method_id:
        method_structural_id = queries.resolve_method_id(conn, snapshot_id, method_id)
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, method_structural_id
        )
    if not resolved_module_id and function_id:
        function_structural_id = queries.resolve_function_id(
            conn, snapshot_id, function_id
        )
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, function_structural_id
        )
    if not resolved_module_id:
        raise ValueError("Prompt requires a resolvable module_id.")
    payload = run(
        snapshot_id,
        conn=conn,
        repo_root=repo_root,
        module_id=resolved_module_id,
        include_file_map=include_file_map,
    )
    return render_json_payload(payload)

def run(snapshot_id: str, **params) -> ModuleOverviewPayload:
    conn = params.get("conn")
    if conn is None:
        raise ValueError(
            "module_overview reducer requires an active database connection."
        )
    row = conn.execute(
        "SELECT is_committed FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if not row or not row["is_committed"]:
        raise ValueError("module_overview reducer requires a committed snapshot.")
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="module_overview reducer"
    )
    module_identifier = params.get("module_id")
    include_file_map = bool(params.get("include_file_map"))
    if not module_identifier:
        raise ValueError("module_overview requires 'module_id'.")
    repo_root = params.get("repo_root")
    repo_path = Path(repo_root) if repo_root else None
    if repo_path is None:
        raise ValueError(
            "module_overview requires repo_root for artifact graph traversal."
        )
    artifact_available = artifact_db_available(repo_path)
    if not artifact_available:
        raise ValueError("module_overview reducer requires the artifact database.")

    row = _resolve_module(conn, snapshot_id, module_identifier)
    if row["node_type"] != "module":
        raise ValueError(f"Node '{module_identifier}' is not a module.")
    module_structural_id = row["structural_id"]
    module_name = row["qualified_name"]

    module_ids = _resolve_module_ids(conn, snapshot_id, module_name)
    files = _list_module_files(conn, snapshot_id, module_ids)
    module_file_entries = (
        _module_file_entries(conn, snapshot_id, module_ids) if include_file_map else []
    )
    types = _list_children(conn, snapshot_id, module_ids, "type", repo_path)
    callables = _list_children(
        conn,
        snapshot_id,
        module_ids,
        "callable",
        repo_path,
        recursive=True,
    )
    nested_types = _list_nested_classes(conn, snapshot_id, module_ids, repo_path)
    imports = _list_imports(conn, snapshot_id, module_ids, repo_path)
    language_breakdown = _language_breakdown(conn, snapshot_id, module_ids, repo_path)

    # Scope clamp: no cross-module aggregation or ranking beyond direct structure facts.
    line_span = [row["start_line"], row["end_line"]]
    payload: ModuleOverviewPayload = {
        "projection": "module_overview",
        "projection_version": "1.0",
        "payload_kind": "summary",
        "module_structural_id": module_structural_id,
        "module_qualified_name": module_name,
        "language": row["language"],
        "file_path": row["file_path"],
        "line_span": line_span,
        "start_byte": row["start_byte"],
        "end_byte": row["end_byte"],
        "content_hash": row["content_hash"],
        "line_span_hash": line_span_hash(repo_path, row["file_path"], line_span),
        "files": files,
        "file_count": len(files),
        "types": types,
        "callables": callables,
        "nested_types": nested_types,
        "classes": types,
        "functions": callables,
        "methods": _list_methods(conn, snapshot_id, module_ids, repo_path),
        "nested_classes": nested_types,
        "node_counts": {
            "types": len(types),
            "callables": len(callables),
        },
        "language_breakdown": language_breakdown,
        "imports": imports,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }
    if include_file_map:
        payload["module_files"] = module_file_entries
        payload["module_file_count"] = len(module_file_entries)
    return payload
