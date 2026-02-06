"""Database connection helpers and pooling."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock, local
from typing import Callable, Iterator

from ..runtime import config as runtime_config
from ..runtime.config import defaults
from ..runtime.logging import get_logger
from .core_db import schema as core_schema
from .artifact_db import schema as artifact_schema

_LOGGER = get_logger("data_storage.connections")


def _resolve_db_timeout(repo_root: Path | None) -> float:
    env_override = os.getenv("SCIONA_DB_TIMEOUT")
    if env_override:
        try:
            return float(env_override)
        except ValueError:
            pass
    if repo_root is not None:
        try:
            settings = runtime_config.load_runtime_config(repo_root).database
            return float(settings.timeout)
        except Exception:
            pass
    return float(defaults.DEFAULT_DB_TIMEOUT)


def _base_connect(
    db_path: Path, *, repo_root: Path | None = None
) -> sqlite3.Connection:
    timeout = _resolve_db_timeout(repo_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    uri = f"file:{db_path.as_posix()}?mode=rwc"
    conn = sqlite3.connect(uri, uri=True, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def connect_core(db_path: Path, *, repo_root: Path | None = None) -> sqlite3.Connection:
    conn = _base_connect(db_path, repo_root=repo_root)
    core_schema.ensure_schema(conn)
    return conn


def connect_artifact(
    db_path: Path, *, repo_root: Path | None = None
) -> sqlite3.Connection:
    conn = _base_connect(db_path, repo_root=repo_root)
    artifact_schema.ensure_schema(conn)
    return conn


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


@contextmanager
def core(
    db_path: Path,
    *,
    repo_root: Path | None = None,
) -> Iterator[sqlite3.Connection]:
    with _core_pool.acquire(db_path, repo_root=repo_root) as conn:
        yield conn


@contextmanager
def artifact(
    db_path: Path,
    *,
    repo_root: Path | None = None,
) -> Iterator[sqlite3.Connection]:
    with _artifact_pool.acquire(db_path, repo_root=repo_root) as conn:
        yield conn
