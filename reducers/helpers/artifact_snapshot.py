"""Artifact snapshot validation helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...data_storage.connections import core
from ...data_storage.core_db import store as core_store
from ...pipelines.config import public as config


def require_latest_snapshot(repo_root: Path, snapshot_id: Optional[str]) -> None:
    if not snapshot_id:
        return
    repo_root = repo_root.resolve()
    db_path = config.get_db_path(repo_root)
    if not db_path.exists():
        raise ValueError("Core database missing; cannot validate snapshot.")
    with core(db_path, repo_root=repo_root) as core_conn:
        latest_snapshot_id = core_store.latest_committed_snapshot_id(core_conn)
    if not latest_snapshot_id or snapshot_id != latest_snapshot_id:
        raise ValueError("Artifact data is available only for the latest committed snapshot.")
