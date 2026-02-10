# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Module file map reducer."""

from __future__ import annotations

from typing import List, Optional

from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="module_file_map",
    category="evidence",
    scope="codebase",
    placeholders=("MODULE_FILE_MAP",),
    determinism="strict",
    payload_size_stats=None,
    summary="Module-to-file map with module ids and file paths.",
    lossy=False,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="module_file_map reducer"
    )
    module_ids: Optional[List[str]] = None
    if module_id:
        module_ids = _resolve_module_ids(conn, snapshot_id, module_id)
    rows = conn.execute(
        """
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
        ORDER BY ni.qualified_name
        """,
        (snapshot_id,),
    ).fetchall()
    entries = []
    for row in rows:
        qualified_name = row["qualified_name"]
        if not qualified_name:
            continue
        if module_ids and qualified_name not in module_ids:
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
    body = {
        "module_filter": module_id,
        "count": len(entries),
        "modules": entries,
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
        raise ValueError(
            f"Module '{module_name}' not found in snapshot '{snapshot_id}'."
        )
    return module_ids
