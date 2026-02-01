"""Surface index reducer."""
from __future__ import annotations

from typing import Dict, List

from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

_SURFACE_PREFIXES = {
    "cli": "sciona.cli",
    "pipelines": "sciona.pipelines",
    "reducers": "sciona.reducers",
    "prompts": "sciona.prompts",
    "addons": "sciona.addons",
}

_NODE_TYPES = ("module", "class", "function")

REDUCER_META = ReducerMeta(
    reducer_id="surface_index",
    scope="codebase",
    placeholders=("SURFACE_INDEX",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="summary",
    summary="Namespace-based index of CLI, pipeline, reducer, prompt, and addon surfaces.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    category: str | None = None,
    limit: int | str | None = 200,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="surface_index reducer")
    categories = _select_categories(category)
    limit_value = _normalize_limit(limit)
    surfaces = {}
    for name, prefix in categories.items():
        surfaces[name] = _fetch_surface_entries(conn, snapshot_id, prefix, limit_value)
    body = {
        "category": category,
        "limit": limit_value,
        "surfaces": surfaces,
    }
    return render_json_payload(body)


def _select_categories(category: str | None) -> Dict[str, str]:
    if not category:
        return dict(_SURFACE_PREFIXES)
    normalized = str(category).strip().lower()
    if normalized not in _SURFACE_PREFIXES:
        raise ValueError(f"Unknown surface category '{category}'.")
    return {normalized: _SURFACE_PREFIXES[normalized]}


def _normalize_limit(limit: int | str | None) -> int:
    if limit is None:
        return 200
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise ValueError("surface_index limit must be an integer.")
    if value <= 0:
        raise ValueError("surface_index limit must be positive.")
    return min(value, 1000)


def _fetch_surface_entries(
    conn,
    snapshot_id: str,
    prefix: str,
    limit: int,
) -> List[Dict[str, str]]:
    placeholders = ", ".join("?" for _ in _NODE_TYPES)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ({placeholders})
          AND (ni.qualified_name = ? OR ni.qualified_name LIKE ?)
        ORDER BY ni.qualified_name
        LIMIT ?
        """,
        (snapshot_id, *_NODE_TYPES, prefix, f"{prefix}.%", limit),
    ).fetchall()
    return [
        {
            "structural_id": row["structural_id"],
            "node_type": row["node_type"],
            "language": row["language"],
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
    ]
