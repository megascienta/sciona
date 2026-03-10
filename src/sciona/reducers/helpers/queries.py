# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Core structural query helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

from ...code_analysis.analysis.module_id import module_id_for

NODE_TYPE_MODULE = ("module",)
NODE_TYPE_CLASS = ("classifier",)
NODE_TYPE_CALLABLE = ("callable",)
NODE_TYPE_FILE_BACKED = ("module", "classifier", "callable")


def resolve_callable_id(conn, snapshot_id: str, callable_id: str | None) -> str:
    if callable_id:
        return _resolve_node_id(
            conn,
            snapshot_id,
            callable_id,
            node_types=NODE_TYPE_CALLABLE,
        )
    rows = conn.execute(
        """
        SELECT DISTINCT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'callable'
        ORDER BY sn.structural_id
        """,
        (snapshot_id,),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError(
            "Reducer requires exactly one callable in the snapshot."
        )
    return rows[0]["structural_id"]


def resolve_classifier_id(conn, snapshot_id: str, classifier_id: str | None) -> str:
    if not classifier_id:
        raise ValueError("Classifier identifier is required.")
    return _resolve_node_id(
        conn,
        snapshot_id,
        classifier_id,
        node_types=NODE_TYPE_CLASS,
    )


def list_modules(conn, snapshot_id: str) -> List[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT sn.structural_id, ni.qualified_name, ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
        ORDER BY ni.qualified_name
        """,
        (snapshot_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def module_id_lookup(conn, snapshot_id: str) -> Dict[str, str]:
    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    module_names: Set[str] = {
        row["qualified_name"]
        for row in rows
        if row["node_type"] == "module" and row["qualified_name"]
    }
    lookup: Dict[str, str] = {}
    for row in rows:
        qualified_name = row["qualified_name"]
        if not qualified_name:
            continue
        lookup[row["structural_id"]] = module_id_for(qualified_name, module_names)
    return lookup


def module_id_for_structural(conn, snapshot_id: str, structural_id: str) -> str:
    lookup = module_id_lookup(conn, snapshot_id)
    return lookup.get(structural_id, "")


def module_root_paths(conn, snapshot_id: str, repo_root: Path) -> List[Path]:
    modules = list_modules(conn, snapshot_id)
    if not modules:
        raise ValueError(f"No modules found in snapshot '{snapshot_id}'.")
    roots: set[Path] = set()
    for row in modules:
        file_path = row.get("file_path")
        if not file_path:
            raise ValueError("Module entry missing file_path; cannot assemble context.")
        roots.add(_normalize_repo_relative(repo_root, Path(file_path).parent))
    return sorted(roots, key=lambda path: path.as_posix())


def resolve_module_root(
    conn, snapshot_id: str, module_id: str, repo_root: Path
) -> Path:
    row = conn.execute(
        """
        SELECT ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (ni.structural_id = ? OR ni.qualified_name = ?)
        LIMIT 1
        """,
        (snapshot_id, module_id, module_id),
    ).fetchone()
    if not row or not row["file_path"]:
        raise ValueError(f"Module '{module_id}' not found in snapshot '{snapshot_id}'.")
    return _normalize_repo_relative(repo_root, Path(row["file_path"]).parent)


def collect_file_paths(
    conn,
    snapshot_id: str,
    repo_root: Path,
    *,
    roots: Iterable[Path] | None = None,
    node_types: Sequence[str] | None = NODE_TYPE_FILE_BACKED,
    exclude_languages: Sequence[str] | None = None,
) -> List[Path]:
    node_clause = _in_clause("sn.node_type", node_types) if node_types else ""
    lang_clause = _not_in_clause("sn.language", exclude_languages) if exclude_languages else ""
    params: list[str] = [snapshot_id]
    if node_types:
        params.extend(node_types)
    if exclude_languages:
        params.extend(exclude_languages)
    rows = conn.execute(
        f"""
        SELECT DISTINCT ni.file_path
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
          AND ni.file_path IS NOT NULL
          AND ni.file_path != ''
          {node_clause}
          {lang_clause}
        ORDER BY ni.file_path
        """,
        tuple(params),
    ).fetchall()
    root_list = list(roots) if roots else []
    results: List[Path] = []
    for row in rows:
        raw_path = row["file_path"]
        if not raw_path:
            continue
        rel_path = _normalize_repo_relative(repo_root, Path(raw_path))
        if root_list and not any(rel_path.is_relative_to(root) for root in root_list):
            continue
        results.append(rel_path)
    return results


def fetch_children(
    conn,
    snapshot_id: str,
    parent_structural_id: str,
    edge_types: Sequence[str],
    node_types: Sequence[str] | None = None,
) -> List[dict[str, str]]:
    edge_clause = _in_clause("e.edge_type", edge_types)
    node_clause = _in_clause("sn.node_type", node_types) if node_types else ""
    params = [snapshot_id, parent_structural_id, *edge_types]
    if node_types:
        params.extend(node_types)
    rows = conn.execute(
        f"""
        SELECT ni.structural_id, ni.qualified_name
        FROM edges e
        JOIN structural_nodes sn ON sn.structural_id = e.dst_structural_id
        JOIN node_instances ni
            ON ni.structural_id = e.dst_structural_id
            AND ni.snapshot_id = e.snapshot_id
        WHERE e.snapshot_id = ?
          AND e.src_structural_id = ?
          {edge_clause}
          {node_clause}
        ORDER BY ni.qualified_name
        """,
        tuple(params),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_class_relationships(
    conn,
    snapshot_id: str,
    structural_id: str,
    edge_types: Sequence[str],
    direction: str = "outgoing",
) -> List[dict[str, str]]:
    if direction == "outgoing":
        clause = "e.src_structural_id = ?"
        other_id = "e.dst_structural_id"
    else:
        clause = "e.dst_structural_id = ?"
        other_id = "e.src_structural_id"
    edge_clause = _in_clause("e.edge_type", edge_types)
    params = [snapshot_id, structural_id, *edge_types]
    rows = conn.execute(
        f"""
        SELECT e.edge_type,
               {other_id} AS related_id,
               ni.qualified_name AS related_name
        FROM edges e
        JOIN node_instances ni ON ni.structural_id = {other_id}
            AND ni.snapshot_id = e.snapshot_id
        WHERE e.snapshot_id = ?
          AND {clause}
          {edge_clause}
        """,
        tuple(params),
    ).fetchall()
    return [
        {
            "edge_type": row["edge_type"],
            "related_structural_id": row["related_id"],
            "related_qualified_name": row["related_name"],
        }
        for row in rows
    ]


def _resolve_node_id(
    conn,
    snapshot_id: str,
    identifier: str,
    node_types: Sequence[str],
) -> str:
    clause = _in_clause("sn.node_type", node_types)
    params: list[str] = [snapshot_id]
    params.extend(node_types)
    params.extend([identifier, identifier])
    row = conn.execute(
        f"""
        SELECT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          {clause}
          AND (sn.structural_id = ? OR ni.qualified_name = ?)
        LIMIT 1
        """,
        tuple(params),
    ).fetchone()
    if not row:
        raise ValueError(f"Node '{identifier}' not found in snapshot '{snapshot_id}'.")
    return row["structural_id"]


def _normalize_repo_relative(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        try:
            return path.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError(f"Path '{path}' is outside the repo root.") from exc
    return Path(path.as_posix())


def _in_clause(field: str, values: Sequence[str]) -> str:
    placeholders = ", ".join("?" for _ in values)
    return f"AND {field} IN ({placeholders})"


def _not_in_clause(field: str, values: Sequence[str]) -> str:
    placeholders = ", ".join("?" for _ in values)
    return f"AND {field} NOT IN ({placeholders})"
