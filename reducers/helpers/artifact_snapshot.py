"""Artifact snapshot validation helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...data_storage.connections import core
from ...data_storage.core_db import store as core_store
from ...runtime.paths import get_db_path


def require_latest_snapshot(repo_root: Path, snapshot_id: Optional[str]) -> None:
    if not snapshot_id:
        return
    repo_root = repo_root.resolve()
    db_path = get_db_path(repo_root)
    if not db_path.exists():
        raise ValueError("Core database missing; cannot validate snapshot.")
    with core(db_path, repo_root=repo_root) as core_conn:
        committed_ids = core_store.list_committed_snapshots(core_conn)
    if not committed_ids:
        raise ValueError("Artifact data requires a committed snapshot.")
    if len(committed_ids) != 1:
        raise ValueError("Artifact data requires exactly one committed snapshot state.")
    if snapshot_id != committed_ids[0]:
        raise ValueError("Artifact data is available only for the committed snapshot selected by build.")
