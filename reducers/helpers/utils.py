"""Shared reducer helpers."""
from __future__ import annotations

from collections import Counter

from ...data_storage.core_db import store as core_store


def top_modules(counter: Counter, *, limit: int) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]


def require_latest_committed_snapshot(conn, snapshot_id: str, *, reducer_name: str = "Reducer") -> None:
    latest_snapshot_id = core_store.latest_committed_snapshot_id(conn)
    if not latest_snapshot_id or snapshot_id != latest_snapshot_id:
        raise ValueError(f"{reducer_name} requires the latest committed snapshot.")
