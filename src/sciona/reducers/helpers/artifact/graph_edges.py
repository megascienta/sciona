# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Artifact graph edge helpers."""

from __future__ import annotations

from pathlib import Path
import json
from typing import List, Optional, Sequence, Tuple

from ..shared.context import current_artifact_connection, fallback_artifact_connection


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


def load_rebuild_status_value(repo_root: Path, *, key: str) -> str | None:
    conn = current_artifact_connection()
    owns_connection = False
    if conn is None:
        conn = fallback_artifact_connection(repo_root)
        owns_connection = conn is not None
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT value FROM rebuild_status WHERE key = ?",
            (key,),
        ).fetchone()
        if not row:
            return None
        value = row["value"]
        return value if isinstance(value, str) else None
    finally:
        if owns_connection:
            conn.close()


def load_call_resolution_diagnostics(
    repo_root: Path,
    *,
    snapshot_id: str,
    caller_id: str | None = None,
) -> dict:
    raw = load_rebuild_status_value(
        repo_root,
        key=f"call_resolution_diagnostics:{snapshot_id}",
    )
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    if caller_id:
        by_caller = payload.get("by_caller") or {}
        if not isinstance(by_caller, dict):
            return {}
        entry = by_caller.get(caller_id)
        if not isinstance(entry, dict):
            return {}
        return entry
    return payload
