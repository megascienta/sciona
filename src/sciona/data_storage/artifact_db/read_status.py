# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB read helpers."""

from __future__ import annotations

import sqlite3


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
