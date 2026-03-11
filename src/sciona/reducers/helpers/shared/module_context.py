# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer helpers for module-oriented structural context."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

from ....code_analysis.analysis.module_id import module_id_for

NODE_TYPE_FILE_BACKED = ("module", "classifier", "callable")


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
