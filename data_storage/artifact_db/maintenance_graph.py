"""ArtifactDB graph maintenance routines."""
from __future__ import annotations

from typing import Final

from ..core_db import store as core_store
from . import store as artifact_store

CALL_EDGE_KIND: Final[str] = "CALLS"


def rebuild_graph_index(
    artifact_conn,
    *,
    core_conn,
    snapshot_id: str,
) -> None:
    core_store.validate_snapshot_for_read(core_conn, snapshot_id, require_committed=True)
    artifact_store.reset_graph_index(artifact_conn)
    nodes = core_conn.execute(
        """
        SELECT sn.structural_id, sn.node_type
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    artifact_store.insert_graph_nodes(
        artifact_conn,
        rows=[(row["structural_id"], row["node_type"]) for row in nodes],
    )
    edges = core_conn.execute(
        """
        SELECT src_structural_id, dst_structural_id, edge_type
        FROM edges
        WHERE snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    graph_edges = [
        (row["src_structural_id"], row["dst_structural_id"], row["edge_type"])
        for row in edges
    ]
    call_edges = artifact_conn.execute(
        """
        SELECT caller_id, callee_id
        FROM node_calls
        WHERE valid = 1
        """,
    ).fetchall()
    graph_edges.extend(
        [(row["caller_id"], row["callee_id"], CALL_EDGE_KIND) for row in call_edges]
    )
    artifact_store.insert_graph_edges(artifact_conn, rows=graph_edges)

__all__ = ["CALL_EDGE_KIND", "rebuild_graph_index"]
