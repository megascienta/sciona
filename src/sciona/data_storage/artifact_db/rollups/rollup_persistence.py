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


def reset_rollup_temp_tables(conn) -> None:
    store_rollups.reset_rollup_temp_tables(conn)


def load_module_lookup(conn, rows: Iterable[tuple[str, str]]) -> None:
    store_rollups.load_module_lookup(conn, rows=rows)


def load_method_to_class(conn, rows: Iterable[tuple[str, str]]) -> None:
    store_rollups.load_method_to_class(conn, rows=rows)


def rebuild_module_call_edges(conn) -> None:
    store_rollups.insert_module_call_edges_from_graph(conn)


def rebuild_class_call_edges(conn) -> None:
    store_rollups.insert_class_call_edges_from_graph(conn)


def rebuild_node_fan_stats(conn) -> None:
    store_rollups.insert_node_fan_stats_from_graph(conn)


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


def clear_call_artifacts_for_callers(
    conn,
    *,
    snapshot_id: str,
    caller_ids: Iterable[str],
) -> None:
    write_index.clear_call_artifacts_for_callers(
        conn,
        snapshot_id=snapshot_id,
        caller_ids=caller_ids,
    )


__all__ = [
    "list_call_edges",
    "list_graph_edges",
    "reset_graph_rollups",
    "reset_rollup_temp_tables",
    "load_module_lookup",
    "load_method_to_class",
    "rebuild_module_call_edges",
    "rebuild_class_call_edges",
    "rebuild_node_fan_stats",
    "clear_call_artifacts_for_callers",
    "upsert_node_calls",
    "write_class_call_edges",
    "write_module_call_edges",
    "write_node_fan_stats",
]
