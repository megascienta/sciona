# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB read helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable

from ..sql_utils import SQLITE_MAX_VARS, chunked


def get_node_status(
    conn: sqlite3.Connection,
    node_ids: Iterable[str] | None = None,
) -> dict[str, str]:
    params: list[str] = []
    clauses = []
    node_ids_list: list[str] | None = None
    if node_ids:
        node_ids_list = list(node_ids)
        if len(node_ids_list) <= SQLITE_MAX_VARS:
            placeholders = ",".join("?" for _ in node_ids_list)
            clauses.append(f"node_id IN ({placeholders})")
            params.extend(node_ids_list)
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    statuses: dict[str, str] = {}
    if node_ids_list is not None and len(node_ids_list) > SQLITE_MAX_VARS:
        for batch in chunked(node_ids_list, SQLITE_MAX_VARS):
            placeholders = ",".join("?" for _ in batch)
            rows = conn.execute(
                f"""
                SELECT node_id, status
                FROM node_status
                WHERE node_id IN ({placeholders})
                """,
                tuple(batch),
            ).fetchall()
            for row in rows:
                status = row["status"]
                if isinstance(status, str):
                    statuses[row["node_id"]] = status
        return statuses
    rows = conn.execute(
        f"""
        SELECT node_id, status
        FROM node_status
        {where_clause}
        """,
        tuple(params),
    ).fetchall()
    for row in rows:
        status = row["status"]
        if isinstance(status, str):
            statuses[row["node_id"]] = status
    return statuses


def rebuild_consistent_for_snapshot(
    conn: sqlite3.Connection, *, snapshot_id: str
) -> bool:
    rows = conn.execute(
        """
        SELECT key, value
        FROM rebuild_status
        WHERE key IN ('last_rebuild_start', 'last_rebuild_complete', 'last_rebuild_failed')
        """
    ).fetchall()
    state = {row["key"]: row["value"] for row in rows}
    last_start = state.get("last_rebuild_start")
    last_complete = state.get("last_rebuild_complete")
    last_failed = state.get("last_rebuild_failed")
    if last_complete == snapshot_id and last_failed != snapshot_id:
        return True
    if last_start == snapshot_id and last_complete != snapshot_id:
        return False
    if last_failed == snapshot_id:
        return False
    return last_complete == snapshot_id
