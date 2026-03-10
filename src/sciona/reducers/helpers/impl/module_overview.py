# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Module overview reducer."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ....code_analysis.analysis.orderings import order_nodes, order_strings
from ..shared import queries
from ..artifact_graph_edges import artifact_db_available, load_artifact_edges
from ..shared.profile_utils import fetch_node_instance
from ..shared.render import render_json_payload, require_connection
from ..shared.types import ModuleOverviewPayload
from ..shared.utils import line_span_hash, require_latest_committed_snapshot
from ...metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="module_overview",
    category="structure",
    risk_tier="normal",
    stage="entity_discovery",
    placeholder="MODULE_OVERVIEW",
    summary="Structural summary of a module, including contained classifiers and callables. "
    "Use for architectural inspection. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    callable_id: str | None = None,
    classifier_id: str | None = None,
    include_file_map: bool | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    resolved_module_id = module_id
    if not resolved_module_id and classifier_id:
        classifier_structural_id = queries.resolve_classifier_id(
            conn, snapshot_id, classifier_id
        )
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, classifier_structural_id
        )
    if not resolved_module_id and callable_id:
        callable_structural_id = queries.resolve_callable_id(
            conn, snapshot_id, callable_id
        )
        resolved_module_id = queries.module_id_for_structural(
            conn, snapshot_id, callable_structural_id
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
    classifiers = _list_children(conn, snapshot_id, module_ids, "classifier", repo_path)
    callables = _list_children(
        conn,
        snapshot_id,
        module_ids,
        "callable",
        repo_path,
        recursive=True,
    )
    nested_classifiers = _list_nested_classes(conn, snapshot_id, module_ids, repo_path)
    imports = _list_imports(conn, snapshot_id, module_ids, repo_path)
    language_breakdown = _language_breakdown(conn, snapshot_id, module_ids, repo_path)
    methods = _list_methods(conn, snapshot_id, module_ids, repo_path)

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
        "classifiers": classifiers,
        "callables": callables,
        "functions": callables,
        "methods": methods,
        "nested_classifiers": nested_classifiers,
        "node_counts": {
            "classifiers": len(classifiers),
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
            ni.start_byte,
            ni.end_byte,
            ni.content_hash
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE sn.node_type = 'module' AND ni.snapshot_id = ? AND ni.qualified_name = ?
        LIMIT 1
        """,
        (snapshot_id, identifier),
    ).fetchone()
    if not row:
        raise ValueError(
            f"Module '{identifier}' not found in snapshot '{snapshot_id}'."
        )
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
        raise ValueError(
            f"Module '{module_name}' not found in snapshot '{snapshot_id}'."
        )
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


def _module_file_entries(
    conn, snapshot_id: str, module_ids: List[str]
) -> List[Dict[str, str]]:
    if not module_ids:
        return []
    placeholders = ",".join("?" for _ in module_ids)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id,
               sn.language,
               ni.qualified_name,
               ni.file_path,
               ni.start_line,
               ni.end_line
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND sn.structural_id IN ({placeholders})
        ORDER BY ni.qualified_name
        """,
        (snapshot_id, *module_ids),
    ).fetchall()
    entries = []
    for row in rows:
        qualified_name = row["qualified_name"]
        if not qualified_name:
            continue
        entries.append(
            {
                "module_qualified_name": qualified_name,
                "module_structural_id": row["structural_id"],
                "language": row["language"],
                "file_path": row["file_path"],
                "line_span": [row["start_line"], row["end_line"]],
            }
        )
    return entries


def _list_children(
    conn,
    snapshot_id: str,
    module_ids: List[str],
    node_type: str,
    repo_root: Path,
    *,
    recursive: bool = False,
) -> List[Dict[str, str]]:
    if recursive:
        frontier = list(module_ids)
        visited: set[str] = set(module_ids)
        child_ids: set[str] = set()
        while frontier:
            edges = load_artifact_edges(
                repo_root,
                edge_kinds=["LEXICALLY_CONTAINS"],
                src_ids=frontier,
            )
            next_frontier: list[str] = []
            for _src, dst, _kind in edges:
                if dst in visited:
                    continue
                visited.add(dst)
                child_ids.add(dst)
                next_frontier.append(dst)
            frontier = next_frontier
        child_ids = sorted(child_ids)
    else:
        edges = load_artifact_edges(
            repo_root,
            edge_kinds=["LEXICALLY_CONTAINS"],
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


def _list_imports(
    conn, snapshot_id: str, module_ids: List[str], repo_root: Path
) -> List[Dict[str, str]]:
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
        {
            "module_structural_id": row["structural_id"],
            "module_qualified_name": row["qualified_name"],
        }
        for row in rows
        if row["qualified_name"]
    ]
    order_nodes(entries, key="module_qualified_name")
    return entries


def _language_breakdown(
    conn, snapshot_id: str, module_ids: List[str], repo_root: Path
) -> Dict[str, int]:
    edges = load_artifact_edges(
        repo_root,
        edge_kinds=["LEXICALLY_CONTAINS"],
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
    type_ids = []
    for row in rows:
        language = row["language"]
        if language:
            counts[language] = counts.get(language, 0) + 1
        if row["node_type"] == "classifier":
            type_ids.append(row["structural_id"])
    if type_ids:
        callable_edges = load_artifact_edges(
            repo_root,
            edge_kinds=["LEXICALLY_CONTAINS"],
            src_ids=type_ids,
        )
        callable_ids = sorted({dst for _, dst, _ in callable_edges})
        if callable_ids:
            placeholders = ",".join("?" for _ in callable_ids)
            callable_rows = conn.execute(
                f"""
                SELECT sn.language
                FROM structural_nodes sn
                WHERE sn.structural_id IN ({placeholders})
                """,
                tuple(callable_ids),
            ).fetchall()
            for row in callable_rows:
                language = row["language"]
                if language:
                    counts[language] = counts.get(language, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _list_methods(
    conn, snapshot_id: str, module_ids: List[str], repo_root: Path
) -> List[Dict[str, str]]:
    container_edges = load_artifact_edges(
        repo_root,
        edge_kinds=["LEXICALLY_CONTAINS"],
        src_ids=module_ids,
    )
    type_ids = sorted({dst for _, dst, _ in container_edges})
    if not type_ids:
        return []
    callable_edges = load_artifact_edges(
        repo_root,
        edge_kinds=["LEXICALLY_CONTAINS"],
        src_ids=type_ids,
    )
    callable_ids = sorted({dst for _, dst, _ in callable_edges})
    if not callable_ids:
        return []
    placeholders = ",".join("?" for _ in callable_ids)
    rows = conn.execute(
        f"""
        SELECT DISTINCT ni.structural_id, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
            AND ni.snapshot_id = ?
        WHERE ni.structural_id IN ({placeholders})
          AND sn.node_type = 'callable'
        """,
        (snapshot_id, *callable_ids),
    ).fetchall()
    entries = [
        {"structural_id": row["structural_id"], "qualified_name": row["qualified_name"]}
        for row in rows
        if row["qualified_name"]
    ]
    order_nodes(entries, key="qualified_name")
    return entries


def _list_nested_classes(
    conn, snapshot_id: str, module_ids: List[str], repo_root: Path
) -> List[Dict[str, str]]:
    container_edges = load_artifact_edges(
        repo_root,
        edge_kinds=["LEXICALLY_CONTAINS"],
        src_ids=module_ids,
    )
    type_ids = sorted({dst for _, dst, _ in container_edges})
    if not type_ids:
        return []
    nested_edges = load_artifact_edges(
        repo_root,
        edge_kinds=["LEXICALLY_CONTAINS"],
        src_ids=type_ids,
    )
    nested_edges = [edge for edge in nested_edges if edge[1] in type_ids]
    if not nested_edges:
        return []
    all_ids = sorted({src for src, _, _ in nested_edges} | {dst for _, dst, _ in nested_edges})
    placeholders = ",".join("?" for _ in all_ids)
    rows = conn.execute(
        f"""
        SELECT ni.structural_id, ni.qualified_name
        FROM node_instances ni
        WHERE ni.snapshot_id = ?
          AND ni.structural_id IN ({placeholders})
        """,
        (snapshot_id, *all_ids),
    ).fetchall()
    names = {
        row["structural_id"]: row["qualified_name"]
        for row in rows
        if row["qualified_name"]
    }
    entries = [
        {
            "parent_structural_id": src_id,
            "parent_qualified_name": names.get(src_id, ""),
            "child_structural_id": dst_id,
            "child_qualified_name": names.get(dst_id, ""),
        }
        for src_id, dst_id, _ in nested_edges
        if names.get(src_id) and names.get(dst_id)
    ]
    order_nodes(
        entries,
        key=lambda item: (
            item["parent_qualified_name"],
            item["child_qualified_name"],
        ),
    )
    return entries


__all__ = [
    "REDUCER_META",
    "render",
    "run",
    "_resolve_module",
    "_resolve_module_ids",
    "_list_module_files",
    "_module_file_entries",
    "_list_children",
    "_list_imports",
    "_language_breakdown",
    "_list_methods",
]
