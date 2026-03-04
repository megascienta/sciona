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


def call_site_drop_debug_counts(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    limit: int = 200,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT caller_id,
               caller_qname,
               identifier,
               drop_reason,
               candidate_count,
               callee_kind,
               COUNT(*) AS site_count
        FROM call_sites
        WHERE snapshot_id = ?
          AND resolution_status = 'dropped'
        GROUP BY caller_id, caller_qname, identifier, drop_reason, candidate_count, callee_kind
        ORDER BY site_count DESC, caller_qname, identifier
        LIMIT ?
        """,
        (snapshot_id, limit),
    ).fetchall()
    return [
        {
            "caller_id": row["caller_id"],
            "caller_qname": row["caller_qname"],
            "identifier": row["identifier"],
            "drop_reason": row["drop_reason"],
            "candidate_count": int(row["candidate_count"] or 0),
            "callee_kind": row["callee_kind"],
            "site_count": int(row["site_count"] or 0),
        }
        for row in rows
    ]


def call_site_accept_debug_counts(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    limit: int = 200,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT caller_id,
               caller_qname,
               identifier,
               accepted_callee_id,
               provenance,
               candidate_count,
               callee_kind,
               COUNT(*) AS site_count
        FROM call_sites
        WHERE snapshot_id = ?
          AND resolution_status = 'accepted'
        GROUP BY
            caller_id,
            caller_qname,
            identifier,
            accepted_callee_id,
            provenance,
            candidate_count,
            callee_kind
        ORDER BY site_count DESC, caller_qname, identifier
        LIMIT ?
        """,
        (snapshot_id, limit),
    ).fetchall()
    return [
        {
            "caller_id": row["caller_id"],
            "caller_qname": row["caller_qname"],
            "identifier": row["identifier"],
            "accepted_callee_id": row["accepted_callee_id"],
            "provenance": row["provenance"],
            "candidate_count": int(row["candidate_count"] or 0),
            "callee_kind": row["callee_kind"],
            "site_count": int(row["site_count"] or 0),
        }
        for row in rows
    ]


def call_site_drop_identifier_counts(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT caller_id,
               identifier,
               drop_reason,
               candidate_count,
               callee_kind,
               COUNT(*) AS site_count
        FROM call_sites
        WHERE snapshot_id = ?
          AND resolution_status = 'dropped'
        GROUP BY caller_id, identifier, drop_reason, candidate_count, callee_kind
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        {
            "caller_id": row["caller_id"],
            "identifier": row["identifier"],
            "drop_reason": row["drop_reason"],
            "candidate_count": int(row["candidate_count"] or 0),
            "callee_kind": row["callee_kind"],
            "site_count": int(row["site_count"] or 0),
        }
        for row in rows
    ]


__all__ = [
    "call_site_accept_debug_counts",
    "call_site_caller_status_counts",
    "call_site_drop_identifier_counts",
    "call_site_drop_debug_counts",
]
