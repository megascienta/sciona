"""ArtifactDB persistence helpers."""
from __future__ import annotations

import sqlite3
from typing import Iterable, Mapping, Sequence
from ...runtime.time import utc_now

from ..encoding import bool_to_int
from ..sql_utils import SQLITE_MAX_VARS, chunked, temp_id_table

NODE_STATUS_PRODUCER = "node_status_v1"

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
    entries = [(caller_id, callee_id, bool_to_int(valid), call_hash) for callee_id in callee_ids]
    conn.executemany(
        """
        INSERT INTO node_calls(caller_id, callee_id, valid, call_hash)
        VALUES (?, ?, ?, ?)
        """,
        entries,
    )


def set_node_status(conn: sqlite3.Connection, node_id: str, status: str) -> None:
    ts = utc_now()
    conn.execute(
        """
        INSERT INTO node_status(node_id, status, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            status=excluded.status,
            updated_at=excluded.updated_at
        """,
        (node_id, status, ts),
    )


def rewrite_node_status(
    conn: sqlite3.Connection,
    *,
    statuses: Sequence[tuple[str, str]],
    producer_id: str,
) -> None:
    conn.execute("DELETE FROM node_status")
    for node_id, status in statuses:
        set_node_status(conn, node_id, status)


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


def cleanup_removed_nodes(
    conn: sqlite3.Connection,
    current_node_ids: Iterable[str],
) -> None:
    ids = list(current_node_ids)
    if not ids:
        conn.execute("DELETE FROM node_status")
        conn.execute("DELETE FROM node_calls")
        return
    with temp_id_table(conn, ids, column="node_id", prefix="current_nodes") as table:
        conn.execute(
            f"DELETE FROM node_status WHERE node_id NOT IN (SELECT node_id FROM {table})",
        )
        conn.execute(
            f"DELETE FROM node_calls WHERE caller_id NOT IN (SELECT node_id FROM {table})",
        )
        conn.execute(
            f"DELETE FROM node_calls WHERE callee_id NOT IN (SELECT node_id FROM {table})",
        )


def reset_graph_index(conn: sqlite3.Connection) -> None:
    """
    Clear graph tables. Build pipeline should call this before rebuilding index.
    """
    conn.execute("DELETE FROM graph_edges")
    conn.execute("DELETE FROM graph_nodes")

def insert_graph_nodes(conn: sqlite3.Connection, *, rows: Iterable[tuple[str, str]]) -> None:
    """
    rows: (node_id, node_kind)
    """
    conn.executemany(
        "INSERT OR REPLACE INTO graph_nodes(node_id, node_kind) VALUES (?, ?)",
        list(rows),
    )

def insert_graph_edges(conn: sqlite3.Connection, *, rows: Iterable[tuple[str, str, str]]) -> None:
    """
    rows: (src_node_id, dst_node_id, edge_kind)
    """
    conn.executemany(
        """
        INSERT OR IGNORE INTO graph_edges(src_node_id, dst_node_id, edge_kind)
        VALUES (?, ?, ?)
        """,
        list(rows),
    )
