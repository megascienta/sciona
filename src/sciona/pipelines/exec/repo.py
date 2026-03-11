# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Repository execution helpers over resolved repository state.

This module intentionally avoids repo discovery and policy decisions. Those
concerns live in `pipelines.ops` and `pipelines.policy`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Optional

from ...runtime.common import constants as setup_config
from ...runtime.config.io import write_default_config
from ...runtime.logging import get_logger
from ..domain.repository import RepoState

_LOGGER = get_logger("pipelines.exec.repo")
from ...data_storage.connections import core
from ...data_storage.core_db import read_ops as core_read
from ..ops import setup as versioning
from ..errors import ConfigError


@dataclass(frozen=True)
class StatusResult:
    repo_root: Path
    sciona_dir: Path
    tool_version: str
    schema_version: str
    snapshot_count: int
    latest_snapshot: Optional[str]
    latest_created: Optional[str]
    db_exists: bool


def init_repo(repo_state: RepoState) -> Path:
    sciona_dir = repo_state.sciona_dir
    if sciona_dir.exists():
        raise ConfigError(
            ".sciona already exists here.",
            code="already_initialized",
            hint="Remove the .sciona directory if you want to reinitialize.",
        )
    versioning.write_version_file(sciona_dir)
    write_default_config(repo_state.repo_root)
    return sciona_dir


def status_repo(repo_state: RepoState) -> StatusResult:
    sciona_dir = repo_state.sciona_dir
    version_info = versioning.read_version_file(sciona_dir)
    versioning.ensure_schema_version(version_info, repo_state.repo_root)

    db_path = repo_state.db_path
    db_exists = db_path.exists()
    snapshot_count = 0
    latest_snapshot: Optional[str] = None
    latest_created: Optional[str] = None
    if db_exists:
        with core(db_path, repo_root=repo_state.repo_root) as conn:
            snapshot_count = core_read.count_committed_snapshots(conn)
            latest_meta = core_read.latest_committed_snapshot(conn)
            if latest_meta:
                latest_snapshot = latest_meta["snapshot_id"]
                latest_created = latest_meta["created_at"]
    return StatusResult(
        repo_root=repo_state.repo_root,
        sciona_dir=repo_state.sciona_dir,
        tool_version=setup_config.TOOL_VERSION,
        schema_version=setup_config.SCHEMA_VERSION,
        snapshot_count=snapshot_count,
        latest_snapshot=latest_snapshot,
        latest_created=latest_created,
        db_exists=db_exists,
    )


def clean_repo(repo_state: RepoState) -> bool:
    sciona_dir = repo_state.sciona_dir
    expected_dir = repo_state.repo_root / ".sciona"
    if sciona_dir != expected_dir:
        raise ConfigError(
            "Refusing to clean a non-canonical SCIONA directory.",
            code="unsafe_clean_path",
        )
    if not sciona_dir.exists():
        return False
    if sciona_dir.is_symlink():
        raise ConfigError(
            "Refusing to clean a symlinked SCIONA directory.",
            code="unsafe_clean_path",
        )
    if sciona_dir.resolve() != expected_dir.resolve():
        raise ConfigError(
            "Refusing to clean a SCIONA directory outside the repository root.",
            code="unsafe_clean_path",
        )
    shutil.rmtree(sciona_dir)
    return True


__all__ = [
    "StatusResult",
    "clean_repo",
    "init_repo",
    "status_repo",
]
