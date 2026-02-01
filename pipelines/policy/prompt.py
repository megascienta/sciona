"""Prompt policy helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..errors import WorkflowError
from ..config import public as config
from ..policy import repo as repo_policy
from ...data_storage.core_db import store as core_store


def ensure_prompt_preconditions(repo_root: Optional[Path] = None) -> Path:
    repo_state = repo_policy.resolve_repo_state(repo_root, allow_missing_config=True)
    repo_policy.ensure_initialized(repo_state)
    return repo_state.repo_root


def resolve_latest_snapshot(conn) -> str:
    latest_snapshot_id = core_store.latest_committed_snapshot_id(conn)
    if not latest_snapshot_id:
        raise WorkflowError(
            "No committed snapshots available. Run 'sciona build' first.",
            code="missing_snapshot",
        )
    return latest_snapshot_id
