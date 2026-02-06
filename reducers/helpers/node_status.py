"""Node status payload helper."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ...data_storage.artifact_db import read_status as artifact_read
from ...data_storage.core_db import read_ops as core_read
from .context import current_artifact_connection, fallback_artifact_connection
from .utils import require_latest_committed_snapshot


def build_node_status_payload(
    snapshot_id: str, *, conn, repo_root: Path
) -> Dict[str, object]:
    if conn is None:
        raise ValueError("node_status payload requires an active database connection.")
    if not repo_root:
        raise ValueError("node_status payload requires repo_root.")
    if not core_read.snapshot_is_committed(conn, snapshot_id):
        raise ValueError("node_status payload requires a committed snapshot.")
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="node_status payload"
    )
    artifact_conn = current_artifact_connection()
    owns_connection = False
    if artifact_conn is None:
        artifact_conn = fallback_artifact_connection(repo_root)
        owns_connection = artifact_conn is not None
    if artifact_conn is None:
        raise ValueError("node_status payload requires the artifact database.")
    try:
        statuses = artifact_read.get_node_status(artifact_conn)
    finally:
        if owns_connection:
            artifact_conn.close()

    rows = core_read.list_nodes_with_names(conn, snapshot_id)
    entries: List[Dict[str, object]] = []
    by_status: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    for node_id, node_type, qualified_name in rows:
        status = statuses.get(node_id, "unknown")
        entries.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "qualified_name": qualified_name,
                "status": status,
            }
        )
        by_status[status] = by_status.get(status, 0) + 1
        by_type[node_type] = by_type.get(node_type, 0) + 1
    return {
        "projection": "node_status",
        "projection_version": "1.0",
        "nodes": entries,
        "counts": {
            "total": len(entries),
            "by_status": dict(sorted(by_status.items())),
            "by_type": dict(sorted(by_type.items())),
        },
    }
