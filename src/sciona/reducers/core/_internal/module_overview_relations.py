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
