# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dependency edge reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ...helpers.render import render_json_payload, require_connection
from ...helpers.utils import require_latest_committed_snapshot
from ...metadata import ReducerMeta

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
    module_ids = [row["structural_id"] for row in rows]
    if not module_ids:
        raise ValueError(
            f"Module '{module_name}' not found in snapshot '{snapshot_id}'."
        )
    return module_ids

def _resolve_module_query(conn, snapshot_id: str, query: str) -> List[str]:
    normalized = str(query).strip()
    if not normalized:
        raise ValueError("dependency_edges query must be non-empty.")
    lowered = normalized.lower()
    rows = conn.execute(
        """
        SELECT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (sn.structural_id = ? OR LOWER(ni.qualified_name) LIKE ?)
        ORDER BY ni.qualified_name
        """,
        (snapshot_id, normalized, f"%{lowered}%"),
    ).fetchall()
    module_ids = [row["structural_id"] for row in rows]
    if not module_ids:
        raise ValueError(
            f"No modules match query '{normalized}' in snapshot '{snapshot_id}'."
        )
    return module_ids

def _node_lookup(
    conn, snapshot_id: str, node_ids: set[str]
) -> Dict[str, Dict[str, str]]:
    if not node_ids:
        return {}
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id, ni.qualified_name, ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
            AND ni.snapshot_id = ?
        WHERE sn.structural_id IN ({placeholders})
        """,
        (snapshot_id, *node_ids),
    ).fetchall()
    return {
        row["structural_id"]: {
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
    }
