"""Node status payload helper."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ...data_storage.artifact_db import connect as artifact_connect
from ...data_storage.artifact_db import store as artifact_store
from ...pipelines.config import public as config
from .utils import require_latest_committed_snapshot


def build_node_status_payload(snapshot_id: str, *, conn, repo_root: Path) -> Dict[str, object]:
    if conn is None:
        raise ValueError("node_status payload requires an active database connection.")
    if not repo_root:
        raise ValueError("node_status payload requires repo_root.")
    row = conn.execute(
        "SELECT is_committed FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if not row or not row["is_committed"]:
        raise ValueError("node_status payload requires a committed snapshot.")
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="node_status payload")
    artifact_path = config.get_artifact_db_path(Path(repo_root))
    if not artifact_path.exists():
        raise ValueError("node_status payload requires the artifact database.")

    artifact_conn = artifact_connect(artifact_path)
    try:
        statuses = artifact_store.get_node_status(artifact_conn)
    finally:
        artifact_conn.close()

    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        ORDER BY sn.node_type, ni.qualified_name
        """,
        (snapshot_id,),
    ).fetchall()
    entries: List[Dict[str, object]] = []
    by_status: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    for row in rows:
        node_id = row["structural_id"]
        node_type = row["node_type"]
        status = statuses.get(node_id, "unknown")
        entries.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "qualified_name": row["qualified_name"],
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
