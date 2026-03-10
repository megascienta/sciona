# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB graph maintenance routines."""

from __future__ import annotations

from itertools import chain
from typing import Final

from ...core_db import read_ops as core_read
from ..writes import write_graph

CALL_EDGE_KIND: Final[str] = "CALLS"


def rebuild_graph_index(
    artifact_conn,
    *,
    core_conn,
    snapshot_id: str,
    progress_factory=None,
) -> None:
    core_read.validate_snapshot_for_read(core_conn, snapshot_id, require_committed=True)
    progress = progress_factory("Rebuilding graph index", 4) if progress_factory else None
    write_graph.reset_graph_index(artifact_conn)
    if progress:
        progress.advance(1)
    nodes = core_read.list_structural_nodes(core_conn, snapshot_id)
    write_graph.insert_graph_nodes(
        artifact_conn,
        rows=nodes,
    )
    if progress:
        progress.advance(1)
    graph_edges = core_read.list_edges(core_conn, snapshot_id)
    call_edges = artifact_conn.execute(
        """
        SELECT caller_id, callee_id
        FROM node_calls
        WHERE valid = 1
        """,
    ).fetchall()
    write_graph.insert_graph_edges(
        artifact_conn,
        rows=chain(
            graph_edges,
            (
                (row["caller_id"], row["callee_id"], CALL_EDGE_KIND)
                for row in call_edges
            ),
        ),
    )
    if progress:
        progress.advance(2)
        progress.close()


__all__ = ["CALL_EDGE_KIND", "rebuild_graph_index"]
