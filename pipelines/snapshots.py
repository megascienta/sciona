"""Snapshot access helpers for pipeline consumers."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import public as config
from .errors import WorkflowError
from .policy import repo as repo_policy
from ..data_storage.connections import core
from ..data_storage.core_db import store as core_store


def latest_committed_snapshot_id(repo_root: Optional[Path] = None) -> str:
    repo_state = repo_policy.resolve_repo_state(repo_root, allow_missing_config=True)
    repo_policy.ensure_initialized(repo_state)
    db_path = config.get_db_path(repo_state.repo_root)
    if not db_path.exists():
        raise WorkflowError(
            "No committed snapshots available. Run 'sciona build' first.",
            code="missing_snapshot",
        )
    with core(db_path, repo_root=repo_state.repo_root) as conn:
        snapshot_id = core_store.latest_committed_snapshot_id(conn)
    if not snapshot_id:
        raise WorkflowError(
            "No committed snapshots available. Run 'sciona build' first.",
            code="missing_snapshot",
        )
    return snapshot_id


__all__ = ["latest_committed_snapshot_id"]
