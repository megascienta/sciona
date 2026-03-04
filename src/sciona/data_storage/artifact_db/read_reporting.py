# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB reporting reads."""

from __future__ import annotations

import sqlite3


def call_site_caller_status_counts(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT caller_id,
               resolution_status,
               drop_reason,
               COUNT(*) AS site_count
        FROM call_sites
        WHERE snapshot_id = ?
        GROUP BY caller_id, resolution_status, drop_reason
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        {
            "caller_id": row["caller_id"],
            "resolution_status": row["resolution_status"],
            "drop_reason": row["drop_reason"],
            "site_count": int(row["site_count"] or 0),
        }
        for row in rows
    ]


__all__ = ["call_site_caller_status_counts"]
