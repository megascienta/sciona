"""Reducer runtime context for DB handles owned by pipelines."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

from ...data_storage.artifact_db import connect as artifact_connect

_ARTIFACT_CONN: ContextVar[object | None] = ContextVar("reducer_artifact_conn", default=None)


def current_artifact_connection() -> object | None:
    return _ARTIFACT_CONN.get()


def fallback_artifact_connection(repo_root: object | None) -> object | None:
    if repo_root is None:
        return None
    root = Path(repo_root)
    artifact_path = root / ".sciona" / "sciona.artifacts.db"
    if not artifact_path.exists():
        return None
    return artifact_connect(artifact_path, repo_root=root)


@contextmanager
def use_artifact_connection(conn: object | None) -> Iterator[None]:
    token = _ARTIFACT_CONN.set(conn)
    try:
        yield
    finally:
        _ARTIFACT_CONN.reset(token)


__all__ = [
    "current_artifact_connection",
    "fallback_artifact_connection",
    "use_artifact_connection",
]
