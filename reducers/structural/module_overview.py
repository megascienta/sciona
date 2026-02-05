"""Module overview reducer."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...code_analysis.analysis.orderings import order_nodes, order_strings
from ..helpers import queries
from ..helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ..helpers.profile_utils import fetch_node_instance
from ..helpers.render import render_json_payload, require_connection
from ..helpers.types import ModuleOverviewPayload
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="module_overview",
    scope="module",
    placeholders=("MODULE_OVERVIEW",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="evidence",
    summary="Structural overview payload for a module.",
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
    **_: object,
) -> str:
    conn = require_connection(conn)
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    resolved_module_id = module_id
    if not resolved_module_id and class_id:
        class_structural_id = queries.resolve_class_id(conn, snapshot_id, class_id)
        resolved_module_id = queries.module_id_for_structural(conn, snapshot_id, class_structural_id)
    if not resolved_module_id and method_id:
        method_structural_id = queries.resolve_method_id(conn, snapshot_id, method_id)
        resolved_module_id = queries.module_id_for_structural(conn, snapshot_id, method_structural_id)
    if not resolved_module_id and function_id:
        function_structural_id = queries.resolve_function_id(conn, snapshot_id, function_id)
        resolved_module_id = queries.module_id_for_structural(conn, snapshot_id, function_structural_id)
    if not resolved_module_id:
        raise ValueError("Prompt requires a resolvable module_id.")
    payload = run(snapshot_id, conn=conn, repo_root=repo_root, module_id=resolved_module_id)
    return render_json_payload(payload)


def run(snapshot_id: str, **params) -> ModuleOverviewPayload:
    conn = params.get("conn")
    if conn is None:
        raise ValueError("module_overview reducer requires an active database connection.")
    row = conn.execute(
        "SELECT is_committed FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if not row or not row["is_committed"]:
        raise ValueError("module_overview reducer requires a committed snapshot.")
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="module_overview reducer")
    module_identifier = params.get("module_id")
    if not module_identifier:
        raise ValueError("module_overview requires 'module_id'.")
    repo_root = params.get("repo_root")
    repo_path = Path(repo_root) if repo_root else None
    if repo_path is None:
        raise ValueError("module_overview requires repo_root for artifact graph traversal.")
    artifact_available = artifact_db_available(repo_path)

    row = _resolve_module(conn, snapshot_id, module_identifier)
    if row["node_type"] != "module":
        raise ValueError(f"Node '{module_identifier}' is not a module.")
    module_structural_id = row["structural_id"]
    module_name = row["qualified_name"]

    module_ids = _resolve_module_ids(conn, snapshot_id, module_name)
    files = _list_module_files(conn, snapshot_id, module_ids)
    classes = _list_children(conn, snapshot_id, module_ids, "class", repo_path)
    functions = _list_children(conn, snapshot_id, module_ids, "function", repo_path)
    methods = _list_methods(conn, snapshot_id, module_ids, repo_path)
    imports = _list_imports(conn, snapshot_id, module_ids, repo_path)
    language_breakdown = _language_breakdown(conn, snapshot_id, module_ids, repo_path)

    # Scope clamp: no cross-module aggregation or ranking beyond direct structure facts.
    return {
        "projection": "module_overview",
        "projection_version": "1.0",
        "module_structural_id": module_structural_id,
        "module_qualified_name": module_name,
        "language": row["language"],
        "file_path": row["file_path"],
        "line_span": [row["start_line"], row["end_line"]],
        "content_hash": row["content_hash"],
        "files": files,
        "file_count": len(files),
        "classes": classes,
        "functions": functions,
        "methods": methods,
        "node_counts": {
            "classes": len(classes),
            "functions": len(functions),
            "methods": len(methods),
        },
        "language_breakdown": language_breakdown,
        "imports": imports,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }


def _resolve_module(conn, snapshot_id: str, identifier: str) -> dict:
    try:
        return fetch_node_instance(conn, snapshot_id, identifier)
    except ValueError:
        pass
    row = conn.execute(
        """
        SELECT
            sn.structural_id,
            sn.node_type,
            sn.language,
            ni.qualified_name,
            ni.file_path,
            ni.start_line,
            ni.end_line,
            ni.content_hash
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE sn.node_type = 'module' AND ni.snapshot_id = ? AND ni.qualified_name = ?
        LIMIT 1
        """,
        (snapshot_id, identifier),
    ).fetchone()
    if not row:
        raise ValueError(f"Module '{identifier}' not found in snapshot '{snapshot_id}'.")
    return row


def _resolve_module_ids(conn, snapshot_id: str, module_name: str) -> List[str]:
    rows = conn.execute(
        """
        SELECT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (ni.qualified_name = ? OR ni.qualified_name LIKE ?)
        ORDER BY ni.qualified_name
        """,
        (snapshot_id, module_name, f"{module_name}.%"),
    ).fetchall()
    module_ids = [row["structural_id"] for row in rows]
    if not module_ids:
        raise ValueError(f"Module '{module_name}' not found in snapshot '{snapshot_id}'.")
    return module_ids


def _list_module_files(conn, snapshot_id: str, module_ids: List[str]) -> List[str]:
    placeholders = ",".join("?" for _ in module_ids)
    rows = conn.execute(
        f"""
        SELECT DISTINCT file_path
        FROM node_instances
        WHERE snapshot_id = ? AND structural_id IN ({placeholders})
        """,
        (snapshot_id, *module_ids),
    ).fetchall()
    files = [row["file_path"] for row in rows if row["file_path"]]
    order_strings(files)
    return files


def _list_children(
    conn,
    snapshot_id: str,
    module_ids: List[str],
    node_type: str,
    repo_root: Path,
) -> List[Dict[str, str]]:
    edges = load_artifact_edges(
        repo_root,
        edge_kinds=["CONTAINS"],
        src_ids=module_ids,
    )
    child_ids = sorted({dst for _, dst, _ in edges})
    if not child_ids:
        return []
    placeholders = ",".join("?" for _ in child_ids)
    rows = conn.execute(
        f"""
        SELECT DISTINCT ni.structural_id, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
            AND ni.snapshot_id = ?
        WHERE ni.structural_id IN ({placeholders})
          AND sn.node_type = ?
        """,
        (snapshot_id, *child_ids, node_type),
    ).fetchall()
    entries = [
        {"structural_id": row["structural_id"], "qualified_name": row["qualified_name"]}
        for row in rows
        if row["qualified_name"]
    ]
    order_nodes(entries, key="qualified_name")
    return entries


def _list_imports(conn, snapshot_id: str, module_ids: List[str], repo_root: Path) -> List[Dict[str, str]]:
    edges = load_artifact_edges(
        repo_root,
        edge_kinds=["IMPORTS_DECLARED"],
        src_ids=module_ids,
    )
    module_ids_out = sorted({dst for _, dst, _ in edges})
    if not module_ids_out:
        return []
    placeholders = ",".join("?" for _ in module_ids_out)
    rows = conn.execute(
        f"""
        SELECT DISTINCT ni.structural_id, ni.qualified_name
        FROM node_instances ni
        WHERE ni.snapshot_id = ?
          AND ni.structural_id IN ({placeholders})
        """,
        (snapshot_id, *module_ids_out),
    ).fetchall()
    entries = [
        {"module_structural_id": row["structural_id"], "module_qualified_name": row["qualified_name"]}
        for row in rows
        if row["qualified_name"]
    ]
    order_nodes(entries, key="module_qualified_name")
    return entries


def _language_breakdown(conn, snapshot_id: str, module_ids: List[str], repo_root: Path) -> Dict[str, int]:
    edges = load_artifact_edges(
        repo_root,
        edge_kinds=["CONTAINS"],
        src_ids=module_ids,
    )
    child_ids = sorted({dst for _, dst, _ in edges})
    if not child_ids:
        return {}
    placeholders = ",".join("?" for _ in child_ids)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id, sn.language, sn.node_type
        FROM structural_nodes sn
        WHERE sn.structural_id IN ({placeholders})
        """,
        tuple(child_ids),
    ).fetchall()
    counts: Dict[str, int] = {}
    class_ids = []
    for row in rows:
        language = row["language"]
        if language:
            counts[language] = counts.get(language, 0) + 1
        if row["node_type"] == "class":
            class_ids.append(row["structural_id"])
    if class_ids:
        method_edges = load_artifact_edges(
            repo_root,
            edge_kinds=["DEFINES_METHOD"],
            src_ids=class_ids,
        )
        method_ids = sorted({dst for _, dst, _ in method_edges})
        if method_ids:
            placeholders = ",".join("?" for _ in method_ids)
            method_rows = conn.execute(
                f"""
                SELECT sn.language
                FROM structural_nodes sn
                WHERE sn.structural_id IN ({placeholders})
                """,
                tuple(method_ids),
            ).fetchall()
            for row in method_rows:
                language = row["language"]
                if language:
                    counts[language] = counts.get(language, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _list_methods(conn, snapshot_id: str, module_ids: List[str], repo_root: Path) -> List[Dict[str, str]]:
    container_edges = load_artifact_edges(
        repo_root,
        edge_kinds=["CONTAINS"],
        src_ids=module_ids,
    )
    class_ids = sorted({dst for _, dst, _ in container_edges})
    if not class_ids:
        return []
    method_edges = load_artifact_edges(
        repo_root,
        edge_kinds=["DEFINES_METHOD"],
        src_ids=class_ids,
    )
    method_ids = sorted({dst for _, dst, _ in method_edges})
    if not method_ids:
        return []
    placeholders = ",".join("?" for _ in method_ids)
    rows = conn.execute(
        f"""
        SELECT DISTINCT ni.structural_id, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
            AND ni.snapshot_id = ?
        WHERE ni.structural_id IN ({placeholders})
          AND sn.node_type = 'method'
        """,
        (snapshot_id, *method_ids),
    ).fetchall()
    entries = [
        {"structural_id": row["structural_id"], "qualified_name": row["qualified_name"]}
        for row in rows
        if row["qualified_name"]
    ]
    order_nodes(entries, key="qualified_name")
    return entries
