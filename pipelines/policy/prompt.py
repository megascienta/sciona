"""Prompt policy helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..errors import WorkflowError
from ..policy import repo as repo_policy
from ...data_storage.core_db import store as core_store


def ensure_prompt_preconditions(repo_root: Optional[Path] = None) -> Path:
    repo_state = repo_policy.resolve_repo_state(repo_root, allow_missing_config=True)
    repo_policy.ensure_initialized(repo_state)
    return repo_state.repo_root


def resolve_latest_snapshot(conn) -> str:
    committed_ids = core_store.list_committed_snapshots(conn)
    if not committed_ids:
        raise WorkflowError(
            "No committed snapshots available. Run 'sciona build' first.",
            code="missing_snapshot",
        )
    if len(committed_ids) != 1:
        raise WorkflowError(
            "Invalid snapshot state: expected exactly one committed snapshot. Run `sciona build`.",
            code="invalid_snapshot_state",
        )
    return committed_ids[0]
