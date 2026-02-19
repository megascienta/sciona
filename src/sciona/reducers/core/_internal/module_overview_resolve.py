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
