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


def _ensure_temp_rejected_callsites_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TEMP TABLE IF NOT EXISTS rejected_callsites_temp (
            caller_structural_id TEXT NOT NULL,
            caller_qualified_name TEXT NOT NULL,
            caller_module TEXT,
            caller_language TEXT,
            caller_file_path TEXT NOT NULL,
            identifier TEXT NOT NULL,
            status TEXT NOT NULL,
            accepted_callee_id TEXT,
            provenance TEXT,
            drop_reason TEXT,
            candidate_count INTEGER NOT NULL,
            callee_kind TEXT NOT NULL,
            call_start_byte INTEGER,
            call_end_byte INTEGER,
            call_ordinal INTEGER NOT NULL,
            in_scope_candidate_count INTEGER,
            candidate_module_hints TEXT,
            gate_reason TEXT NOT NULL,
            raw_drop_reason TEXT
        )
        """
    )


def reset_temp_rejected_callsites(conn: sqlite3.Connection) -> None:
    _ensure_temp_rejected_callsites_table(conn)
    conn.execute("DELETE FROM rejected_callsites_temp")


def store_temp_rejected_callsites(
    conn: sqlite3.Connection,
    *,
    caller_structural_id: str,
    caller_qualified_name: str,
    caller_module: str | None,
    caller_language: str | None,
    caller_file_path: str,
    rows: Sequence[tuple],
) -> None:
    if not rows:
        return
    _ensure_temp_rejected_callsites_table(conn)
    conn.executemany(
        """
        INSERT INTO rejected_callsites_temp(
            caller_structural_id,
            caller_qualified_name,
            caller_module,
            caller_language,
            caller_file_path,
            identifier,
            status,
            accepted_callee_id,
            provenance,
            drop_reason,
            candidate_count,
            callee_kind,
            call_start_byte,
            call_end_byte,
            call_ordinal,
            in_scope_candidate_count,
            candidate_module_hints,
            gate_reason,
            raw_drop_reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                caller_structural_id,
                caller_qualified_name,
                caller_module,
                caller_language,
                caller_file_path,
                row[0][0],
                row[0][1],
                row[0][2],
                row[0][3],
                row[0][4],
                row[0][5],
                row[0][6],
                row[0][7],
                row[0][8],
                row[0][9],
                row[0][10],
                row[0][11],
                row[1],
                row[2],
            )
            for row in rows
        ],
    )


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


def set_snapshot_summary(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    value: str,
) -> None:
    _set_rebuild_status(conn, key=f"snapshot_summary:{snapshot_id}", value=value)
