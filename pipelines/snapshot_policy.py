"""Snapshot lifecycle policy decisions."""
from __future__ import annotations

from typing import Iterable, List

from ..data_storage.core_db import store as core_store
from ..data_storage.sql_utils import temp_id_table


def select_evictions(committed_snapshots: Iterable[str], retention_limit: int) -> List[str]:
    """Return snapshot IDs to evict given the retention limit."""
    if retention_limit < 1:
        raise ValueError(
            f"Invalid retention_limit: {retention_limit}. Must be >= 1."
        )
    ordered = list(committed_snapshots)
    return ordered[retention_limit:]


def rotate_committed_snapshots(conn, retention_limit: int) -> List[str]:
    """Delete committed snapshots beyond the retention limit."""
    committed = core_store.list_committed_snapshots(conn)
    to_delete = select_evictions(committed, retention_limit)
    if not to_delete:
        return []
    with temp_id_table(conn, to_delete, column="snapshot_id", prefix="snapshot_ids") as table:
        conn.execute(
            f"DELETE FROM node_instances WHERE snapshot_id IN (SELECT snapshot_id FROM {table})",
        )
        conn.execute(
            f"DELETE FROM edges WHERE snapshot_id IN (SELECT snapshot_id FROM {table})",
        )
        conn.execute(
            f"DELETE FROM snapshots WHERE snapshot_id IN (SELECT snapshot_id FROM {table})",
        )
    return to_delete


__all__ = ["rotate_committed_snapshots", "select_evictions"]
