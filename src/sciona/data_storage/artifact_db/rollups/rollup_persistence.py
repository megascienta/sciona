# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Persistence helpers for artifact rollups and call artifacts."""

from __future__ import annotations

from typing import Iterable, Sequence

from . import store_rollups
from ..writes import write_index


def reset_graph_rollups(conn) -> None:
    store_rollups.reset_graph_rollups(conn)


def list_call_edges(conn) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT src_node_id, dst_node_id
        FROM graph_edges
        WHERE edge_kind = ?
        """,
        ("CALLS",),
    ).fetchall()
    return [(row["src_node_id"], row["dst_node_id"]) for row in rows]


def list_graph_edges(conn) -> list[tuple[str, str, str]]:
    rows = conn.execute(
        """
        SELECT src_node_id, dst_node_id, edge_kind
        FROM graph_edges
        """,
    ).fetchall()
    return [(row["src_node_id"], row["dst_node_id"], row["edge_kind"]) for row in rows]


def list_persisted_callsite_callees(
    conn,
    *,
    snapshot_id: str,
    caller_id: str,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT accepted_callee_id
        FROM call_sites
        WHERE snapshot_id = ?
          AND caller_id = ?
          AND resolution_status = 'accepted'
          AND accepted_callee_id IS NOT NULL
        ORDER BY accepted_callee_id
        """,
        (snapshot_id, caller_id),
    ).fetchall()
    return [row["accepted_callee_id"] for row in rows]


def write_module_call_edges(conn, rows: Iterable[tuple[str, str, int]]) -> None:
    payload = list(rows)
    if not payload:
        return
    store_rollups.insert_module_call_edges(conn, rows=payload)


def write_class_call_edges(conn, rows: Iterable[tuple[str, str, int]]) -> None:
    payload = list(rows)
    if not payload:
        return
    store_rollups.insert_class_call_edges(conn, rows=payload)


def write_node_fan_stats(conn, rows: Iterable[tuple[str, str, str, int, int]]) -> None:
    payload = list(rows)
    if not payload:
        return
    store_rollups.insert_node_fan_stats(conn, rows=payload)


def upsert_node_calls(
    conn,
    *,
    caller_id: str,
    callee_ids: Sequence[str],
    call_hash: str,
) -> None:
    write_index.upsert_node_calls(
        conn,
        caller_id=caller_id,
        callee_ids=callee_ids,
        valid=True,
        call_hash=call_hash,
    )


def upsert_call_sites(
    conn,
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
    write_index.upsert_call_sites(
        conn,
        snapshot_id=snapshot_id,
        caller_id=caller_id,
        caller_qname=caller_qname,
        caller_node_type=caller_node_type,
        rows=rows,
    )


__all__ = [
    "list_call_edges",
    "list_persisted_callsite_callees",
    "list_graph_edges",
    "reset_graph_rollups",
    "upsert_call_sites",
    "upsert_node_calls",
    "write_class_call_edges",
    "write_module_call_edges",
    "write_node_fan_stats",
]
