"""Database helpers for SCIONA."""

from . import schema


def connect(db_path, *, repo_root=None):
    from ..connections import connect_core

    return connect_core(db_path, repo_root=repo_root)


__all__ = ["connect", "schema"]
