# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB read helpers."""

from __future__ import annotations

import json
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


def build_wall_seconds_for_snapshot(
    conn: sqlite3.Connection, *, snapshot_id: str
) -> float | None:
    raw = rebuild_status_value(conn, key=f"build_wall_seconds:{snapshot_id}")
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value >= 0.0 else None


def build_phase_timings_for_snapshot(
    conn: sqlite3.Connection, *, snapshot_id: str
) -> dict[str, float] | None:
    raw = rebuild_status_value(conn, key=f"build_phase_timings:{snapshot_id}")
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    result: dict[str, float] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number < 0.0:
            continue
        result[key] = number
    return result


def call_resolution_diagnostics_for_snapshot(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
) -> dict[str, object] | None:
    raw = rebuild_status_value(conn, key=f"call_resolution_diagnostics:{snapshot_id}")
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
