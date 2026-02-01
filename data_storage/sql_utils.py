"""Shared SQLite helpers."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, Iterator, Sequence
from uuid import uuid4

SQLITE_MAX_VARS = 900


def chunked(values: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    if size < 1:
        raise ValueError("chunk size must be >= 1")
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]


@contextmanager
def temp_id_table(
    conn,
    ids: Sequence[str],
    *,
    column: str = "node_id",
    prefix: str = "temp_ids",
) -> Iterator[str]:
    if column not in _VALID_COLUMNS:
        raise ValueError(f"Invalid column name: {column}")
    if prefix not in _VALID_PREFIXES:
        raise ValueError(f"Invalid prefix: {prefix}")
    table_name = f"{prefix}_{uuid4().hex}"
    conn.execute(f"CREATE TEMP TABLE {table_name} ({column} TEXT PRIMARY KEY)")
    try:
        for batch in chunked(list(ids), SQLITE_MAX_VARS):
            conn.executemany(
                f"INSERT INTO {table_name}({column}) VALUES (?)",
                [(value,) for value in batch],
            )
        yield table_name
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")


_VALID_PREFIXES = frozenset({"temp_ids", "snapshot_ids", "current_nodes"})
_VALID_COLUMNS = frozenset({"node_id", "snapshot_id"})
