# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""File outline reducer."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .helpers.shared import queries
from .helpers.shared.render import render_json_payload, require_connection
from .helpers.shared.utils import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="file_outline",
    category="navigation",
    placeholder="FILE_OUTLINE",
    summary="Structural outline of a file, including modules, classifiers, and callables. " \
    "Use for navigation and symbol discovery. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    file_path: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="file_outline reducer"
    )
    module_ids: Optional[List[str]] = None
    file_filter: Optional[set[str]] = None
    if module_id:
        module_ids = _resolve_module_ids(conn, snapshot_id, module_id)
    if file_path:
        normalized = _normalize_file_path(repo_root, file_path)
        file_filter = {normalized}
    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path,
               ni.start_line,
               ni.end_line
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ('module', 'type', 'callable')
        ORDER BY ni.file_path, ni.start_line, ni.qualified_name
        """,
        (snapshot_id,),
    ).fetchall()
    module_lookup = queries.module_id_lookup(conn, snapshot_id)
    grouped: Dict[str, dict] = {}
    for row in rows:
        file_entry = row["file_path"]
        if not file_entry:
            continue
        if file_filter and file_entry not in file_filter:
            continue
        module_name = module_lookup.get(row["structural_id"])
        if module_ids and module_name not in module_ids:
            continue
        node = {
            "structural_id": row["structural_id"],
            "qualified_name": row["qualified_name"],
            "node_type": row["node_type"],
            "module_qualified_name": module_name,
            "line_span": [row["start_line"], row["end_line"]],
            "row_origin": "committed",
        }
        if file_entry not in grouped:
            grouped[file_entry] = {
                "file_path": file_entry,
                "language": row["language"],
                "nodes": [],
            }
        grouped[file_entry]["nodes"].append(node)
    files = []
    for file_key in sorted(grouped):
        entry = grouped[file_key]
        entry["nodes"] = sorted(
            entry["nodes"],
            key=lambda item: (
                item["line_span"][0],
                item["line_span"][1],
                str(item["qualified_name"]),
            ),
        )
        files.append(entry)
    body = {
        "payload_kind": "summary",
        "module_filter": module_id,
        "file_path": file_path,
        "count": len(files),
        "files": files,
    }
    return render_json_payload(body)


def _resolve_module_ids(conn, snapshot_id: str, module_name: str) -> List[str]:
    rows = conn.execute(
        """
        SELECT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (ni.qualified_name = ? OR ni.qualified_name LIKE ? OR sn.structural_id = ?)
        ORDER BY ni.qualified_name
        """,
        (snapshot_id, module_name, f"{module_name}.%", module_name),
    ).fetchall()
    module_structural_ids = [row["structural_id"] for row in rows]
    if not module_structural_ids:
        raise ValueError(
            f"Module '{module_name}' not found in snapshot '{snapshot_id}'."
        )
    module_lookup = queries.module_id_lookup(conn, snapshot_id)
    resolved: List[str] = []
    seen: set[str] = set()
    for structural_id in module_structural_ids:
        module_id = module_lookup.get(structural_id)
        if module_id and module_id not in seen:
            resolved.append(module_id)
            seen.add(module_id)
    if not resolved:
        raise ValueError(
            f"Module '{module_name}' not found in snapshot '{snapshot_id}'."
        )
    return resolved


def _normalize_file_path(repo_root, path_value: str) -> str:
    normalized = str(path_value).strip()
    if not normalized:
        raise ValueError("file_outline file_path must be non-empty.")
    if repo_root is None:
        return normalized
    repo_root = Path(repo_root).resolve()
    raw_path = Path(normalized)
    if raw_path.is_absolute():
        try:
            return str(raw_path.resolve().relative_to(repo_root))
        except ValueError as exc:
            raise ValueError(
                "file_outline file_path must be within the repo root."
            ) from exc
    return raw_path.as_posix()
