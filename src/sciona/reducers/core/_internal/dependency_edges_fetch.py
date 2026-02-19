# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dependency edge reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ...helpers.render import render_json_payload, require_connection
from ...helpers.utils import require_latest_committed_snapshot
from ...metadata import ReducerMeta

def _fetch_edges(
    conn,
    snapshot_id: str,
    from_ids: Optional[List[str]],
    to_ids: Optional[List[str]],
    edge_type: str | None,
    limit: int | None,
) -> List[Dict[str, str]]:
    clauses = [
        "e.snapshot_id = ?",
        "sn_src.node_type = 'module'",
        "sn_dst.node_type = 'module'",
    ]
    params: list[object] = [snapshot_id]
    if edge_type:
        clauses.append("e.edge_type = ?")
        params.append(edge_type)
    if from_ids:
        placeholders = ",".join("?" for _ in from_ids)
        clauses.append(f"e.src_structural_id IN ({placeholders})")
        params.extend(from_ids)
    if to_ids:
        placeholders = ",".join("?" for _ in to_ids)
        clauses.append(f"e.dst_structural_id IN ({placeholders})")
        params.extend(to_ids)
    where = " AND ".join(clauses)
    limit_clause = " LIMIT ?" if limit else ""
    if limit:
        params.append(limit)
    rows = conn.execute(
        f"""
        SELECT e.src_structural_id, e.dst_structural_id, e.edge_type
        FROM edges e
        JOIN structural_nodes sn_src ON sn_src.structural_id = e.src_structural_id
        JOIN structural_nodes sn_dst ON sn_dst.structural_id = e.dst_structural_id
        WHERE {where}
        ORDER BY e.src_structural_id, e.dst_structural_id
        {limit_clause}
        """,
        params,
    ).fetchall()
    return [
        {
            "from_module_structural_id": row["src_structural_id"],
            "to_module_structural_id": row["dst_structural_id"],
            "edge_type": row["edge_type"],
        }
        for row in rows
    ]

def _fetch_dependency_edges(
    conn,
    snapshot_id: str,
    *,
    from_ids: Optional[List[str]],
    to_ids: Optional[List[str]],
    edge_type: str | None,
    limit: int | None,
    direction: str,
    module_ids: Optional[List[str]],
) -> List[Dict[str, str]]:
    if module_ids and direction == "both" and from_ids is None and to_ids is None:
        outgoing = _fetch_edges(conn, snapshot_id, module_ids, None, edge_type, limit)
        incoming = _fetch_edges(conn, snapshot_id, None, module_ids, edge_type, limit)
        merged: dict[tuple[str, str, str], Dict[str, str]] = {}
        for entry in outgoing + incoming:
            key = (
                entry.get("from_module_structural_id"),
                entry.get("to_module_structural_id"),
                entry.get("edge_type"),
            )
            merged[key] = entry
        return sorted(
            merged.values(),
            key=lambda item: (
                item.get("from_module_structural_id"),
                item.get("to_module_structural_id"),
                item.get("edge_type"),
            ),
        )
    return _fetch_edges(conn, snapshot_id, from_ids, to_ids, edge_type, limit)
