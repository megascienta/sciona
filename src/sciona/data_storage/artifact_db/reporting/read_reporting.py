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
               in_scope_candidate_count,
               candidate_module_hints,
               COUNT(*) AS site_count
        FROM call_sites
        WHERE snapshot_id = ?
          AND resolution_status = 'dropped'
        GROUP BY caller_id,
                 caller_qname,
                 identifier,
                 drop_reason,
                 candidate_count,
                 callee_kind,
                 in_scope_candidate_count,
                 candidate_module_hints
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
            "in_scope_candidate_count": (
                int(row["in_scope_candidate_count"])
                if row["in_scope_candidate_count"] is not None
                else None
            ),
            "candidate_module_hints": row["candidate_module_hints"],
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
               in_scope_candidate_count,
               candidate_module_hints,
               COUNT(*) AS site_count
        FROM call_sites
        WHERE snapshot_id = ?
          AND resolution_status = 'dropped'
        GROUP BY caller_id,
                 identifier,
                 drop_reason,
                 candidate_count,
                 callee_kind,
                 in_scope_candidate_count,
                 candidate_module_hints
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
            "in_scope_candidate_count": (
                int(row["in_scope_candidate_count"])
                if row["in_scope_candidate_count"] is not None
                else None
            ),
            "candidate_module_hints": row["candidate_module_hints"],
            "site_count": int(row["site_count"] or 0),
        }
        for row in rows
    ]


def call_site_rows_for_caller(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    caller_id: str,
    identifier: str | None = None,
) -> list[dict[str, object]]:
    clauses = ["snapshot_id = ?", "caller_id = ?"]
    params: list[object] = [snapshot_id, caller_id]
    if identifier:
        clauses.append("identifier = ?")
        params.append(identifier)
    where = " AND ".join(clauses)
    rows = conn.execute(
        f"""
        SELECT
            identifier,
            resolution_status,
            accepted_callee_id,
            provenance,
            drop_reason,
            candidate_count,
            callee_kind,
            in_scope_candidate_count,
            candidate_module_hints,
            call_start_byte,
            call_end_byte,
            call_ordinal,
            site_hash
        FROM call_sites
        WHERE {where}
        ORDER BY identifier, call_ordinal, site_hash
        """,
        tuple(params),
    ).fetchall()
    return [dict(row) for row in rows]


__all__ = [
    "call_site_accept_debug_counts",
    "call_site_caller_status_counts",
    "call_site_drop_identifier_counts",
    "call_site_drop_debug_counts",
    "call_site_rows_for_caller",
]
