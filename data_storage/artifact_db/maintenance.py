"""ArtifactDB maintenance routines that bridge core and artifact stores."""

from __future__ import annotations

from .maintenance_graph import rebuild_graph_index

__all__ = [
    "rebuild_graph_index",
]
