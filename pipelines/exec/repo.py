"""Repository execution helpers (mechanism only)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Optional

from ...runtime import constants as setup_config
from ...runtime.logging import get_logger
from ...runtime.repo_state import RepoState

_LOGGER = get_logger("pipelines.exec.repo")
from ...data_storage.connections import core
from ...runtime import addons as addon_runtime
from ...prompts.bootstrap import ensure_prompts_initialized
from .. import setup as versioning
from ..config import public as config
from ..errors import ConfigError
from .build import BuildResult, build_repo, seed_initial_snapshots
from ..policy.build import resolve_build_policy
from ..policy import repo as policy_repo


@dataclass(frozen=True)
class RebuildResult:
    sciona_dir: Path
    removed_existing: bool
    restored_config: bool
    build_result: BuildResult


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
    config.write_default_config(repo_state.repo_root)
    ensure_prompts_initialized(repo_state.repo_root)
    addon_registry = addon_runtime.load(repo_state.repo_root)
    addon_runtime.run_inits(addon_registry, repo_root=repo_state.repo_root)
    return sciona_dir


def rebuild_repo(repo_state: RepoState) -> RebuildResult:
    sciona_dir = repo_state.sciona_dir
    existing_config = config.load_config_text(repo_state.repo_root)
    removed_existing = False
    if sciona_dir.exists():
        shutil.rmtree(sciona_dir)
        removed_existing = True
    versioning.write_version_file(sciona_dir)
    restored_config = False
    if existing_config is not None:
        config.write_config_text(repo_state.repo_root, existing_config)
        restored_config = True
    else:
        config.write_default_config(repo_state.repo_root)
    ensure_prompts_initialized(repo_state.repo_root)
    addon_registry = addon_runtime.load(repo_state.repo_root)
    addon_runtime.run_inits(addon_registry, repo_root=repo_state.repo_root)
    refreshed_state = RepoState.from_repo_root(repo_state.repo_root, git=repo_state.git)
    policy = resolve_build_policy(refreshed_state)
    dirty_tree = policy_repo.is_worktree_dirty_for_languages(
        refreshed_state, policy.analysis.languages
    )
    seed_initial_snapshots(refreshed_state, policy, dirty_tree)
    result = build_repo(refreshed_state, policy)
    return RebuildResult(
        sciona_dir=sciona_dir,
        removed_existing=removed_existing,
        restored_config=restored_config,
        build_result=result,
    )


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
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM snapshots WHERE is_committed = 1"
            ).fetchone()
            snapshot_count = row["count"] if row and row["count"] is not None else 0
            latest_row = conn.execute(
                """
                SELECT snapshot_id, created_at
                FROM snapshots
                WHERE is_committed = 1
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
            if latest_row:
                latest_snapshot = latest_row["snapshot_id"]
                latest_created = latest_row["created_at"]
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
    if not sciona_dir.exists():
        return False
    shutil.rmtree(sciona_dir)
    return True


__all__ = [
    "BuildResult",
    "RebuildResult",
    "StatusResult",
    "clean_repo",
    "init_repo",
    "rebuild_repo",
    "status_repo",
]
