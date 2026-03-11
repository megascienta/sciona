# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer helpers for structural relationships."""

from __future__ import annotations

from typing import Sequence


def fetch_children(
    conn,
    snapshot_id: str,
    parent_structural_id: str,
    edge_types: Sequence[str],
    node_types: Sequence[str] | None = None,
) -> list[dict[str, str]]:
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
) -> list[dict[str, str]]:
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


def _in_clause(field: str, values: Sequence[str]) -> str:
    placeholders = ", ".join("?" for _ in values)
    return f"AND {field} IN ({placeholders})"
