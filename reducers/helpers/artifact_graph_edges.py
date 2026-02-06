"""Artifact graph edge helpers."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .context import current_artifact_connection, fallback_artifact_connection


def load_artifact_edges(
    repo_root: Path,
    *,
    edge_kinds: Optional[Sequence[str]] = None,
    exclude_kinds: Optional[Sequence[str]] = None,
    src_ids: Optional[Sequence[str]] = None,
    dst_ids: Optional[Sequence[str]] = None,
) -> List[Tuple[str, str, str]]:
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
        if edge_kinds:
            placeholders = ",".join("?" for _ in edge_kinds)
            clauses.append(f"edge_kind IN ({placeholders})")
            params.extend(edge_kinds)
        if exclude_kinds:
            placeholders = ",".join("?" for _ in exclude_kinds)
            clauses.append(f"edge_kind NOT IN ({placeholders})")
            params.extend(exclude_kinds)
        if src_ids:
            placeholders = ",".join("?" for _ in src_ids)
            clauses.append(f"src_node_id IN ({placeholders})")
            params.extend(src_ids)
        if dst_ids:
            placeholders = ",".join("?" for _ in dst_ids)
            clauses.append(f"dst_node_id IN ({placeholders})")
            params.extend(dst_ids)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT src_node_id, dst_node_id, edge_kind
            FROM graph_edges
            {where}
            """,
            tuple(params),
        ).fetchall()
        return [
            (row["src_node_id"], row["dst_node_id"], row["edge_kind"]) for row in rows
        ]
    finally:
        if owns_connection:
            conn.close()


def artifact_db_available(repo_root: Path) -> bool:
    conn = current_artifact_connection()
    owns_connection = False
    if conn is None:
        conn = fallback_artifact_connection(repo_root)
        owns_connection = conn is not None
    if conn is None:
        return False
    try:
        return True
    finally:
        if owns_connection:
            conn.close()
