# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB read helpers."""

from __future__ import annotations

import sqlite3


def rebuild_status_value(conn: sqlite3.Connection, *, key: str) -> str | None:
    row = conn.execute(
        """
        SELECT value
        FROM rebuild_status
        WHERE key = ?
        """,
        (key,),
    ).fetchone()
    if row is None:
        return None
    value = row["value"]
    return value if isinstance(value, str) else None


def rebuild_consistent_for_snapshot(
    conn: sqlite3.Connection, *, snapshot_id: str
) -> bool:
    last_start = rebuild_status_value(conn, key="last_rebuild_start")
    last_complete = rebuild_status_value(conn, key="last_rebuild_complete")
    last_failed = rebuild_status_value(conn, key="last_rebuild_failed")
    if last_complete == snapshot_id and last_failed != snapshot_id:
        return True
    if last_start == snapshot_id and last_complete != snapshot_id:
        return False
    if last_failed == snapshot_id:
        return False
    return last_complete == snapshot_id


def build_total_seconds_for_snapshot(
    conn: sqlite3.Connection, *, snapshot_id: str
) -> float | None:
    raw = rebuild_status_value(conn, key=f"build_total_seconds:{snapshot_id}")
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value >= 0.0 else None
