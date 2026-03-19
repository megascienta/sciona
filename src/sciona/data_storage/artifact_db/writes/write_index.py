# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB write/index helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable, Sequence

from ....runtime.common.time import utc_now
from ...common.encoding import bool_to_int
from ...common.sql_utils import temp_id_table
def reset_artifact_derived_state(conn: sqlite3.Connection) -> None:
    """Clear all rebuild-derived artifact tables before repopulating them."""
    conn.execute("DELETE FROM node_calls")
    conn.execute("DELETE FROM graph_edges")
    conn.execute("DELETE FROM graph_nodes")
    conn.execute("DELETE FROM module_call_edges")
    conn.execute("DELETE FROM class_call_edges")
    conn.execute("DELETE FROM node_fan_stats")


def upsert_node_calls(
    conn: sqlite3.Connection,
    *,
    caller_id: str,
    callee_ids: Sequence[str],
    valid: bool = True,
    call_hash: str,
) -> None:
    """
    Replace (delete+insert) all outgoing calls for a caller_id.

    This is intentionally keyed and explicit; higher-level build logic decides
    which callers to refresh.
    """
    conn.execute("DELETE FROM node_calls WHERE caller_id = ?", (caller_id,))
    if not callee_ids:
        return
    entries = [
        (caller_id, callee_id, bool_to_int(valid), call_hash)
        for callee_id in callee_ids
    ]
    conn.executemany(
        """
        INSERT INTO node_calls(caller_id, callee_id, valid, call_hash)
        VALUES (?, ?, ?, ?)
        """,
        entries,
    )


def cleanup_removed_nodes(
    conn: sqlite3.Connection,
    current_node_ids: Iterable[str],
) -> None:
    ids = list(current_node_ids)
    if not ids:
        conn.execute("DELETE FROM node_calls")
        return
    with temp_id_table(conn, ids, column="node_id", prefix="current_nodes") as table:
        conn.execute(
            f"DELETE FROM node_calls WHERE caller_id NOT IN (SELECT node_id FROM {table})",
        )
        conn.execute(
            f"DELETE FROM node_calls WHERE callee_id NOT IN (SELECT node_id FROM {table})",
        )
def clear_call_artifacts_for_callers(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    caller_ids: Iterable[str],
) -> None:
    del snapshot_id
    caller_list = list(caller_ids)
    if not caller_list:
        return
    placeholders = ",".join("?" for _ in caller_list)
    conn.execute(
        f"DELETE FROM node_calls WHERE caller_id IN ({placeholders})",
        caller_list,
    )


def mark_rebuild_started(conn: sqlite3.Connection, *, snapshot_id: str) -> None:
    _set_rebuild_status(conn, key="last_rebuild_start", value=snapshot_id)


def mark_rebuild_completed(conn: sqlite3.Connection, *, snapshot_id: str) -> None:
    _set_rebuild_status(conn, key="last_rebuild_complete", value=snapshot_id)


def mark_rebuild_failed(conn: sqlite3.Connection, *, snapshot_id: str) -> None:
    _set_rebuild_status(conn, key="last_rebuild_failed", value=snapshot_id)


def _set_rebuild_status(conn: sqlite3.Connection, *, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO rebuild_status(key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=excluded.updated_at
        """,
        (key, value, utc_now()),
    )


def set_rebuild_metadata(conn: sqlite3.Connection, *, key: str, value: str) -> None:
    _set_rebuild_status(conn, key=key, value=value)
