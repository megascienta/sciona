# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer helpers for resolving structural identifiers."""

from __future__ import annotations

from typing import Sequence

NODE_TYPE_CLASS = ("classifier",)
NODE_TYPE_CALLABLE = ("callable",)


def resolve_callable_id(conn, snapshot_id: str, callable_id: str | None) -> str:
    if callable_id:
        return _resolve_node_id(
            conn,
            snapshot_id,
            callable_id,
            node_types=NODE_TYPE_CALLABLE,
        )
    rows = conn.execute(
        """
        SELECT DISTINCT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'callable'
        ORDER BY sn.structural_id
        """,
        (snapshot_id,),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError("Reducer requires exactly one callable in the snapshot.")
    return rows[0]["structural_id"]


def resolve_classifier_id(conn, snapshot_id: str, classifier_id: str | None) -> str:
    if not classifier_id:
        raise ValueError("Classifier identifier is required.")
    return _resolve_node_id(
        conn,
        snapshot_id,
        classifier_id,
        node_types=NODE_TYPE_CLASS,
    )


def _resolve_node_id(
    conn,
    snapshot_id: str,
    identifier: str,
    node_types: Sequence[str],
) -> str:
    clause = _in_clause("sn.node_type", node_types)
    params: list[str] = [snapshot_id]
    params.extend(node_types)
    params.extend([identifier, identifier])
    row = conn.execute(
        f"""
        SELECT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          {clause}
          AND (sn.structural_id = ? OR ni.qualified_name = ?)
        LIMIT 1
        """,
        tuple(params),
    ).fetchone()
    if not row:
        raise ValueError(f"Node '{identifier}' not found in snapshot '{snapshot_id}'.")
    return row["structural_id"]


def _in_clause(field: str, values: Sequence[str]) -> str:
    placeholders = ", ".join("?" for _ in values)
    return f"AND {field} IN ({placeholders})"
