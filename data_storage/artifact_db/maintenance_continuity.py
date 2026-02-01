"""ArtifactDB continuity maintenance routines."""
from __future__ import annotations

from ..sql_utils import temp_id_table
from . import store as artifact_store


def rebuild_node_continuity(
    artifact_conn,
    *,
    core_conn,
    snapshot_id: str,
) -> None:
    artifact_conn.execute("DELETE FROM node_continuity")
    snapshot_rows = core_conn.execute(
        """
        SELECT snapshot_id
        FROM snapshots
        WHERE is_committed = 1
        ORDER BY created_at ASC
        """,
    ).fetchall()
    snapshot_ids = [row["snapshot_id"] for row in snapshot_rows]
    window_size = len(snapshot_ids)
    if window_size == 0:
        return
    node_rows = core_conn.execute(
        "SELECT structural_id FROM node_instances WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchall()
    node_ids = [row["structural_id"] for row in node_rows]
    if not node_ids:
        return
    with temp_id_table(core_conn, snapshot_ids, column="snapshot_id", prefix="snapshot_ids") as table:
        counts = core_conn.execute(
            f"""
            SELECT structural_id, COUNT(DISTINCT snapshot_id) AS cnt
            FROM node_instances
            WHERE snapshot_id IN (SELECT snapshot_id FROM {table})
            GROUP BY structural_id
            """,
        ).fetchall()
    count_map = {row["structural_id"]: row["cnt"] for row in counts}
    for node_id in node_ids:
        survived = int(count_map.get(node_id, 0))
        confidence = survived / window_size if window_size else 0.0
        volatility = 1.0 - confidence if window_size else 0.0
        artifact_store.upsert_node_continuity(
            artifact_conn,
            node_id=node_id,
            window_size=window_size,
            survived_count=survived,
            renamed=False,
            moved=False,
            split_from=None,
            volatility_score=volatility,
            confidence=confidence,
        )
