"""Public surface index reducer."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ..helpers import queries
from ..helpers.profile_utils import (
    python_function_extras,
    typescript_function_extras,
)
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="public_surface_index",
    scope="codebase",
    placeholders=("PUBLIC_SURFACE_INDEX",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="summary",
    summary="Index of public classes and callables with signatures.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    kind: str | None = None,
    limit: int | str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="public_surface_index reducer")
    repo_root_path = Path(repo_root) if repo_root else None
    module_ids: Optional[List[str]] = None
    if module_id:
        module_ids = _resolve_module_ids(conn, snapshot_id, module_id)
    node_types = _normalize_kind(kind)
    limit_value = _normalize_limit(limit)
    module_lookup = queries.module_id_lookup(conn, snapshot_id)
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
          AND sn.node_type IN ('class', 'function', 'method')
        ORDER BY ni.qualified_name
        """,
        (snapshot_id,),
    ).fetchall()
    entries = []
    for row in rows:
        if row["node_type"] not in node_types:
            continue
        qualified_name = row["qualified_name"] or ""
        name = qualified_name.split(".")[-1] if qualified_name else ""
        if not _is_public(name):
            continue
        module_name = module_lookup.get(row["structural_id"], "")
        if module_ids and module_name not in module_ids:
            continue
        signature = None
        if row["node_type"] in {"function", "method"}:
            signature = _build_signature(
                name,
                _function_parameters(
                    row["language"],
                    repo_root_path,
                    row["file_path"],
                    row["start_line"],
                    row["end_line"],
                ),
            )
        entries.append(
            {
                "name": name,
                "qualified_name": qualified_name,
                "kind": row["node_type"],
                "structural_id": row["structural_id"],
                "module_id": module_name,
                "file_path": row["file_path"],
                "signature": signature,
            }
        )
        if limit_value is not None and len(entries) >= limit_value:
            break
    body = {
        "module_id": module_id,
        "kind": kind,
        "limit": limit_value,
        "count": len(entries),
        "symbols": entries,
    }
    return render_json_payload(body)


def _resolve_module_ids(conn, snapshot_id: str, module_name: str) -> List[str]:
    rows = conn.execute(
        """
        SELECT ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (ni.qualified_name = ? OR ni.qualified_name LIKE ? OR sn.structural_id = ?)
        ORDER BY ni.qualified_name
        """,
        (snapshot_id, module_name, f"{module_name}.%", module_name),
    ).fetchall()
    module_ids = [row["qualified_name"] for row in rows if row["qualified_name"]]
    if not module_ids:
        raise ValueError(f"Module '{module_name}' not found in snapshot '{snapshot_id}'.")
    return module_ids


def _function_parameters(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> List[str]:
    if language == "python":
        params, _has_docstring, _span, _decorators = python_function_extras(
            language,
            repo_root,
            file_path,
            start_line,
            end_line,
        )
        return params
    if language == "typescript":
        params, _decorators = typescript_function_extras(
            language,
            repo_root,
            file_path,
            start_line,
            end_line,
        )
        return params
    return []


def _build_signature(name: str, parameters: List[str]) -> str:
    args = ", ".join(parameters)
    return f"{name}({args})" if name else f"({args})"


def _is_public(name: str) -> bool:
    return bool(name) and not name.startswith("_")


def _normalize_kind(kind: Optional[str]) -> List[str]:
    if not kind:
        return ["class", "function", "method"]
    normalized = str(kind).strip().lower()
    if normalized in {"any", "all"}:
        return ["class", "function", "method"]
    if normalized == "callable":
        return ["function", "method"]
    if normalized in {"class", "function", "method"}:
        return [normalized]
    raise ValueError(f"Unknown kind '{kind}'.")


def _normalize_limit(limit: int | str | None) -> int | None:
    if limit is None:
        return None
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise ValueError("public_surface_index limit must be an integer.")
    if value <= 0:
        raise ValueError("public_surface_index limit must be positive.")
    return min(value, 200)
