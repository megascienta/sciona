"""ArtifactDB persistence helpers."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence
from ...runtime.time import utc_now

from ..encoding import bool_to_int, int_to_bool
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


@dataclass(frozen=True)
class NodeContinuityRecord:
    node_id: str
    window_size: int
    survived_count: int
    renamed: bool
    moved: bool
    split_from: str | None
    volatility_score: float
    confidence: float
    computed_at: str

def upsert_node_continuity(
    conn: sqlite3.Connection,
    *,
    node_id: str,
    window_size: int,
    survived_count: int,
    renamed: bool,
    moved: bool,
    split_from: str | None,
    volatility_score: float,
    confidence: float,
    computed_at: str | None = None,
) -> None:
    _validate_continuity(window_size, survived_count, volatility_score, confidence)
    ts = computed_at or utc_now()
    conn.execute(
        """
        INSERT INTO node_continuity(
            node_id, window_size, survived_count, renamed, moved, split_from,
            volatility_score, confidence, computed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            window_size=excluded.window_size,
            survived_count=excluded.survived_count,
            renamed=excluded.renamed,
            moved=excluded.moved,
            split_from=excluded.split_from,
            volatility_score=excluded.volatility_score,
            confidence=excluded.confidence,
            computed_at=excluded.computed_at
        """,
        (
            node_id,
            window_size,
            survived_count,
            bool_to_int(renamed),
            bool_to_int(moved),
            split_from,
            float(volatility_score),
            float(confidence),
            ts,
        ),
    )


def _validate_continuity(
    window_size: int,
    survived_count: int,
    volatility_score: float,
    confidence: float,
) -> None:
    max_int = 2**31 - 1
    if window_size < 0 or window_size > max_int:
        raise ValueError(f"window_size out of range: {window_size}")
    if survived_count < 0 or survived_count > window_size:
        raise ValueError(f"survived_count invalid: {survived_count}/{window_size}")
    if not (0.0 <= float(volatility_score) <= 1.0):
        raise ValueError(f"volatility_score out of range: {volatility_score}")
    if not (0.0 <= float(confidence) <= 1.0):
        raise ValueError(f"confidence out of range: {confidence}")

def get_node_continuity_for_nodes(
    conn: sqlite3.Connection,
    *,
    node_ids: Sequence[str],
) -> dict[str, NodeContinuityRecord]:
    if not node_ids:
        return {}
    out: dict[str, NodeContinuityRecord] = {}
    for batch in chunked(list(node_ids), SQLITE_MAX_VARS):
        placeholders = ",".join(["?"] * len(batch))
        query = """
            SELECT node_id, window_size, survived_count, renamed, moved, split_from,
                   volatility_score, confidence, computed_at
            FROM node_continuity
            WHERE node_id IN ({placeholders})
            """
        query = query.format(placeholders=placeholders)
        rows = conn.execute(query, tuple(batch)).fetchall()
        for r in rows:
            rec = NodeContinuityRecord(
                node_id=r["node_id"],
                window_size=int(r["window_size"]),
                survived_count=int(r["survived_count"]),
                renamed=int_to_bool(r["renamed"]),
                moved=int_to_bool(r["moved"]),
                split_from=r["split_from"],
                volatility_score=float(r["volatility_score"]),
                confidence=float(r["confidence"]),
                computed_at=r["computed_at"],
            )
            out[rec.node_id] = rec
    return out
