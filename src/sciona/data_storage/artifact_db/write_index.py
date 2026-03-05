# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB write/index helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable, Sequence

from ...runtime.time import utc_now
from ..encoding import bool_to_int
from ..sql_utils import temp_id_table
from .write_call_sites import build_site_hash


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
        conn.execute(
            f"DELETE FROM call_sites WHERE caller_id NOT IN (SELECT node_id FROM {table})",
        )


def upsert_call_sites(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    caller_id: str,
    caller_qname: str,
    caller_node_type: str,
    rows: Sequence[
        tuple[
            str,
            str,
            str | None,
            str | None,
            str | None,
            int,
            str,
            int | None,
            int | None,
            int,
            int | None,
            str | None,
        ]
    ],
) -> None:
    conn.execute(
        "DELETE FROM call_sites WHERE snapshot_id = ? AND caller_id = ?",
        (snapshot_id, caller_id),
    )
    if not rows:
        return
    entries = []
    for (
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
    ) in rows:
        site_hash = build_site_hash(
            snapshot_id=snapshot_id,
            caller_id=caller_id,
            identifier=identifier,
            resolution_status=status,
            accepted_callee_id=accepted_callee_id,
            provenance=provenance,
            drop_reason=drop_reason,
            candidate_count=candidate_count,
            callee_kind=callee_kind,
            call_start_byte=call_start_byte,
            call_end_byte=call_end_byte,
            call_ordinal=call_ordinal,
            in_scope_candidate_count=in_scope_candidate_count,
            candidate_module_hints=candidate_module_hints,
        )
        entries.append(
            (
                snapshot_id,
                caller_id,
                caller_qname,
                caller_node_type,
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
                site_hash,
            )
        )
    conn.executemany(
        """
        INSERT INTO call_sites(
            snapshot_id,
            caller_id,
            caller_qname,
            caller_node_type,
            identifier,
            resolution_status,
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
            site_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        entries,
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
