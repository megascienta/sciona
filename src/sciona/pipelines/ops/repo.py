# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Pipeline implementations backing CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional

from ..domain.repository import RepoState
from ..domain.policies import BuildPolicy
from ...runtime.logging import get_logger
from ..hooks import (
    HookStatus,
    install_post_commit_hook,
    post_commit_hook_status,
    remove_post_commit_hook,
)
from ...runtime.agents import setup as agents_runtime
from ...reducers.registry import get_reducers
from ..exec.build import (
    BuildResult,
    build_repo as exec_build,
    record_build_wall_seconds as exec_record_build_wall_seconds,
)
from ..exec.init_dialog import (
    InitDialogDefaults,
    apply_language_selection as exec_apply_language_selection,
    detect_languages as exec_detect_languages,
    supported_languages as exec_supported_languages,
)
from ..exec.repo import (
    StatusResult,
    clean_repo as exec_clean,
    init_repo as exec_init,
    status_repo as exec_status,
)
from ..exec.reporting import snapshot_report as exec_snapshot_report
from ..policy import build as policy_build
from ..policy import repo as policy_repo

logger = get_logger(__name__)


def init(repo_root: Optional[Path] = None) -> Path:
    logger.info("Initializing SCIONA repository.")
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_repo_has_commits(repo_state)
    return exec_init(repo_state)


def init_agents(
    repo_root: Optional[Path],
    *,
    mode: str = "append",
    commands: Mapping[str, str] | None = None,
) -> Path:
    """Generate/update the managed AGENTS.md block.

    commands: optional CLI command map for template placeholders.
    """
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_repo_has_commits(repo_state)
    reducers = get_reducers()
    return agents_runtime.upsert_agents_file(
        repo_state.repo_root, mode=mode, reducers=reducers, commands=commands
    )


def init_dialog_defaults(repo_root: Optional[Path] = None) -> InitDialogDefaults:
    logger.info("Detecting languages for init dialog.")
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_repo_has_commits(repo_state)
    return exec_detect_languages(repo_state.repo_root)


def init_apply_languages(
    selected: list[str],
    repo_root: Optional[Path] = None,
) -> None:
    logger.info("Applying init language selection.")
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_repo_has_commits(repo_state)
    exec_apply_language_selection(repo_state.repo_root, selected)


def init_supported_languages() -> list[str]:
    return exec_supported_languages()


def build(
    repo_root: Optional[Path] = None,
    *,
    force_rebuild: bool = False,
) -> BuildResult:
    logger.info("Building SCIONA snapshot.")
    repo_state = policy_repo.resolve_repo_state(repo_root)
    policy_repo.ensure_repo_has_commits(repo_state)
    policy = policy_build.resolve_build_policy(
        repo_state,
        force_rebuild=force_rebuild,
    )
    policy_repo.ensure_clean_worktree_for_enabled_languages(repo_state)
    return _run_build(repo_state, policy)


def status(repo_root: Optional[Path] = None) -> StatusResult:
    logger.info("Fetching SCIONA status.")
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_initialized(repo_state)
    return exec_status(repo_state)


def snapshot_report(
    snapshot_id: str,
    repo_root: Optional[Path] = None,
    *,
    include_failure_reasons: bool = False,
) -> dict[str, object] | None:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_initialized(repo_state)
    return exec_snapshot_report(
        repo_state,
        snapshot_id=snapshot_id,
        include_failure_reasons=include_failure_reasons,
    )


def record_build_wall_time(
    snapshot_id: str,
    wall_seconds: float,
    repo_root: Optional[Path] = None,
) -> None:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_initialized(repo_state)
    exec_record_build_wall_seconds(
        repo_state=repo_state,
        snapshot_id=snapshot_id,
        wall_seconds=wall_seconds,
    )


def clean(repo_root: Optional[Path] = None) -> bool:
    logger.info("Cleaning SCIONA repository state.")
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    return exec_clean(repo_state)


def install_commit_hook(
    command: str,
    repo_root: Optional[Path] = None,
) -> HookStatus:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    return install_post_commit_hook(repo_state.repo_root, command)


def remove_commit_hook(repo_root: Optional[Path] = None) -> HookStatus:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    return remove_post_commit_hook(repo_state.repo_root)


def commit_hook_status(repo_root: Optional[Path] = None) -> HookStatus:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    return post_commit_hook_status(repo_state.repo_root)


def clean_agents(repo_root: Optional[Path] = None) -> bool:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    return agents_runtime.remove_agents_block(repo_state.repo_root)


def dirty_worktree_warning(repo_root: Optional[Path] = None) -> str | None:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    return policy_repo.dirty_worktree_warning(repo_state)


def _run_build(repo_state: RepoState, policy: BuildPolicy) -> BuildResult:
    policy_repo.ensure_initialized(repo_state)
    policy_repo.ensure_repo_has_commits(repo_state)
    return exec_build(repo_state, policy)
