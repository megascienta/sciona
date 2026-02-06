"""Artifact graph rollup helpers."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .context import current_artifact_connection, fallback_artifact_connection


def load_module_call_edges(
    repo_root: Path,
    *,
    snapshot_id: Optional[str] = None,
    src_module_ids: Optional[Sequence[str]] = None,
    dst_module_ids: Optional[Sequence[str]] = None,
) -> List[Tuple[str, str, int]]:
    del snapshot_id
    conn = current_artifact_connection()
    owns_connection = False
    if conn is None:
        conn = fallback_artifact_connection(repo_root)
        owns_connection = conn is not None
    if conn is None:
        return []
    try:
        clauses: list[str] = []
        params: list[str] = []
        if src_module_ids:
            placeholders = ",".join("?" for _ in src_module_ids)
            clauses.append(f"src_module_id IN ({placeholders})")
            params.extend(src_module_ids)
        if dst_module_ids:
            placeholders = ",".join("?" for _ in dst_module_ids)
            clauses.append(f"dst_module_id IN ({placeholders})")
            params.extend(dst_module_ids)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT src_module_id, dst_module_id, call_count
            FROM module_call_edges
            {where}
            """,
            tuple(params),
        ).fetchall()
        return [
            (row["src_module_id"], row["dst_module_id"], int(row["call_count"]))
            for row in rows
        ]
    finally:
        if owns_connection:
            conn.close()


def load_class_call_edges(
    repo_root: Path,
    *,
    snapshot_id: Optional[str] = None,
    src_class_ids: Optional[Sequence[str]] = None,
    dst_class_ids: Optional[Sequence[str]] = None,
) -> List[Tuple[str, str, int]]:
    del snapshot_id
    conn = current_artifact_connection()
    owns_connection = False
    if conn is None:
        conn = fallback_artifact_connection(repo_root)
        owns_connection = conn is not None
    if conn is None:
        return []
    try:
        clauses: list[str] = []
        params: list[str] = []
        if src_class_ids:
            placeholders = ",".join("?" for _ in src_class_ids)
            clauses.append(f"src_class_id IN ({placeholders})")
            params.extend(src_class_ids)
        if dst_class_ids:
            placeholders = ",".join("?" for _ in dst_class_ids)
            clauses.append(f"dst_class_id IN ({placeholders})")
            params.extend(dst_class_ids)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT src_class_id, dst_class_id, call_count
            FROM class_call_edges
            {where}
            """,
            tuple(params),
        ).fetchall()
        return [
            (row["src_class_id"], row["dst_class_id"], int(row["call_count"]))
            for row in rows
        ]
    finally:
        if owns_connection:
            conn.close()


def load_node_fan_stats(
    repo_root: Path,
    *,
    snapshot_id: Optional[str] = None,
    node_ids: Optional[Sequence[str]] = None,
    edge_kinds: Optional[Sequence[str]] = None,
    node_kinds: Optional[Sequence[str]] = None,
) -> List[Tuple[str, str, str, int, int]]:
    del snapshot_id
    conn = current_artifact_connection()
    owns_connection = False
    if conn is None:
        conn = fallback_artifact_connection(repo_root)
        owns_connection = conn is not None
    if conn is None:
        return []
    try:
        clauses: list[str] = []
        params: list[str] = []
        if node_ids:
            placeholders = ",".join("?" for _ in node_ids)
            clauses.append(f"node_id IN ({placeholders})")
            params.extend(node_ids)
        if edge_kinds:
            placeholders = ",".join("?" for _ in edge_kinds)
            clauses.append(f"edge_kind IN ({placeholders})")
            params.extend(edge_kinds)
        if node_kinds:
            placeholders = ",".join("?" for _ in node_kinds)
            clauses.append(f"node_kind IN ({placeholders})")
            params.extend(node_kinds)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT node_id, node_kind, edge_kind, fan_in, fan_out
            FROM node_fan_stats
            {where}
            """,
            tuple(params),
        ).fetchall()
        return [
            (
                row["node_id"],
                row["node_kind"],
                row["edge_kind"],
                int(row["fan_in"]),
                int(row["fan_out"]),
            )
            for row in rows
        ]
    finally:
        if owns_connection:
            conn.close()
