# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Database connection helpers and pooling.

This module owns connection lifecycle only. Timeout/config resolution lives in
`data_storage.common.connection_settings`.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock, local
from typing import Callable, Iterator
from urllib.parse import quote

from ..runtime.logging import get_logger
from .common.connection_settings import resolve_db_timeout
from .core_db import schema as core_schema
from .artifact_db import schema as artifact_schema

_LOGGER = get_logger("data_storage.connections")
def _base_connect(
    db_path: Path,
    *,
    repo_root: Path | None = None,
    read_only: bool = False,
) -> sqlite3.Connection:
    timeout = resolve_db_timeout(repo_root)
    if not read_only:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "ro" if read_only else "rwc"
    encoded_path = quote(db_path.as_posix(), safe="/")
    uri = f"file:{encoded_path}?mode={mode}"
    conn = sqlite3.connect(uri, uri=True, timeout=timeout)
    conn.row_factory = sqlite3.Row
    if not read_only:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    if read_only:
        conn.execute("PRAGMA query_only=ON")
    return conn


def connect_core(db_path: Path, *, repo_root: Path | None = None) -> sqlite3.Connection:
    conn = _base_connect(db_path, repo_root=repo_root)
    core_schema.ensure_schema(conn)
    return conn


def connect_core_readonly(
    db_path: Path, *, repo_root: Path | None = None
) -> sqlite3.Connection:
    return _base_connect(db_path, repo_root=repo_root, read_only=True)


def connect_artifact(
    db_path: Path, *, repo_root: Path | None = None
) -> sqlite3.Connection:
    conn = _base_connect(db_path, repo_root=repo_root)
    artifact_schema.ensure_schema(conn)
    return conn


def connect_artifact_readonly(
    db_path: Path, *, repo_root: Path | None = None
) -> sqlite3.Connection:
    return _base_connect(db_path, repo_root=repo_root, read_only=True)


class ConnectionPool:
    def __init__(
        self,
        connect_func: Callable[..., sqlite3.Connection],
        max_connections: int = 10,
    ) -> None:
        self._connect_func = connect_func
        self._max_connections = max_connections
        self._state = local()
        self._lock = Lock()

    def _get_pool(self, key: str) -> list[sqlite3.Connection]:
        pools = getattr(self._state, "pools", None)
        if pools is None:
            pools = {}
            self._state.pools = pools
        return pools.setdefault(key, [])

    @contextmanager
    def acquire(
        self, db_path: Path, *, repo_root: Path | None = None
    ) -> Iterator[sqlite3.Connection]:
        key = str(db_path.resolve())
        with self._lock:
            pool = self._get_pool(key)
            conn = (
                pool.pop() if pool else self._connect_func(db_path, repo_root=repo_root)
            )
        try:
            yield conn
        finally:
            if conn.in_transaction:
                try:
                    conn.rollback()
                    _LOGGER.warning("Rolled back a leaked transaction for %s", db_path)
                except Exception:
                    conn.close()
                    return
            with self._lock:
                if len(pool) < self._max_connections:
                    pool.append(conn)
                else:
                    conn.close()


_core_pool = ConnectionPool(connect_core, max_connections=20)
_artifact_pool = ConnectionPool(connect_artifact, max_connections=10)
_core_ro_pool = ConnectionPool(connect_core_readonly, max_connections=20)
_artifact_ro_pool = ConnectionPool(connect_artifact_readonly, max_connections=10)


@contextmanager
def core(
    db_path: Path,
    *,
    repo_root: Path | None = None,
) -> Iterator[sqlite3.Connection]:
    with _core_pool.acquire(db_path, repo_root=repo_root) as conn:
        yield conn


@contextmanager
def core_readonly(
    db_path: Path,
    *,
    repo_root: Path | None = None,
) -> Iterator[sqlite3.Connection]:
    with _core_ro_pool.acquire(db_path, repo_root=repo_root) as conn:
        yield conn


@contextmanager
def artifact(
    db_path: Path,
    *,
    repo_root: Path | None = None,
) -> Iterator[sqlite3.Connection]:
    with _artifact_pool.acquire(db_path, repo_root=repo_root) as conn:
        yield conn


@contextmanager
def artifact_readonly(
    db_path: Path,
    *,
    repo_root: Path | None = None,
) -> Iterator[sqlite3.Connection]:
    with _artifact_ro_pool.acquire(db_path, repo_root=repo_root) as conn:
        yield conn
