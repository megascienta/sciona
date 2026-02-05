"""ArtifactDB namespace (derived, last-committed-snapshot only)."""

from . import maintenance, read_status, schema, write_graph, write_index


def connect(db_path, *, repo_root=None):
    from ..connections import connect_artifact

    return connect_artifact(db_path, repo_root=repo_root)


__all__ = [
    "connect",
    "maintenance",
    "read_status",
    "schema",
    "write_graph",
    "write_index",
]
