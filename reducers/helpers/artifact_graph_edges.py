"""Artifact graph edge helpers."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from ...data_storage.artifact_db import connect as artifact_connect
from ...pipelines.config import public as config
from .artifact_snapshot import require_latest_snapshot


def load_artifact_edges(
    repo_root: Path,
    *,
    snapshot_id: Optional[str] = None,
    edge_kinds: Optional[Sequence[str]] = None,
    exclude_kinds: Optional[Sequence[str]] = None,
    src_ids: Optional[Sequence[str]] = None,
    dst_ids: Optional[Sequence[str]] = None,
) -> List[Tuple[str, str, str]]:
    repo_root = repo_root.resolve()
    require_latest_snapshot(repo_root, snapshot_id)
    artifact_path = config.get_artifact_db_path(repo_root)
    try:
        artifact_path.resolve().relative_to(repo_root)
    except ValueError:
        raise ValueError("Artifact path outside repo root.")
    if not artifact_path.exists():
        return []
    conn = artifact_connect(artifact_path)
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
        return [(row["src_node_id"], row["dst_node_id"], row["edge_kind"]) for row in rows]
    finally:
        conn.close()
