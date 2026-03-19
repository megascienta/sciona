# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""File outline reducer."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .helpers.shared import queries
from .helpers.shared.connection import require_connection
from .helpers.shared.payload import render_json_payload
from .helpers.shared.snapshot_guard import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="file_outline",
    category="navigation",
    placeholder="FILE_OUTLINE",
    summary="Shows the structural outline of one file, including modules, classifiers, "
    "and callables. Use for file-level navigation and symbol discovery. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    file_path: str | None = None,
    compact: bool | None = None,
    depth: int | None = None,
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
    if compact:
        body = _compact_payload(body, depth=depth)
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


def _compact_payload(payload: Dict[str, object], *, depth: int | None) -> Dict[str, object]:
    normalized_depth = _normalize_depth(depth)
    files = list(payload.get("files", []) or [])
    compact_files = [
        {
            "file_path": str(file_entry.get("file_path") or ""),
            "language": file_entry.get("language"),
            "node_counts": _node_counts(file_entry.get("nodes", []) or []),
            "outline_preview": _outline_preview(
                file_entry.get("nodes", []) or [],
                max_depth=normalized_depth,
            ),
        }
        for file_entry in files
    ]
    return {
        "payload_kind": "compact_summary",
        "module_filter": payload.get("module_filter"),
        "file_path": payload.get("file_path"),
        "count": payload.get("count", len(compact_files)),
        "depth": normalized_depth,
        "files": compact_files,
    }


def _normalize_depth(value: int | None) -> int:
    if value is None:
        return 1
    normalized = int(value)
    if normalized < 0:
        raise ValueError("file_outline depth must be zero or greater.")
    return normalized


def _node_counts(nodes: List[dict]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for node in nodes:
        node_type = str(node.get("node_type") or "unknown")
        counts[node_type] = counts.get(node_type, 0) + 1
    return counts


def _outline_preview(nodes: List[dict], *, max_depth: int) -> Dict[str, object]:
    preview = [node for node in nodes if _relative_depth(node) <= max_depth]
    return {
        "count": len(preview),
        "total": len(nodes),
        "truncated": len(preview) < len(nodes),
        "nodes": preview,
    }


def _relative_depth(node: dict) -> int:
    node_type = str(node.get("node_type") or "")
    qualified_name = str(node.get("qualified_name") or "")
    module_name = str(node.get("module_qualified_name") or "")
    if node_type == "module":
        return 0
    if not qualified_name or not module_name:
        return 0
    if qualified_name == module_name:
        return 0
    qualified_parts = qualified_name.split(".")
    module_parts = module_name.split(".")
    return max(0, len(qualified_parts) - len(module_parts))
