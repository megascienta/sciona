"""Pipeline implementations backing CLI commands."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..runtime.repo_state import RepoState
from ..runtime.policies import BuildPolicy
from ..runtime.logging import get_logger
from ..prompts.bootstrap import ensure_prompts_initialized
from ..runtime import agents as agents_runtime
from .exec.build import (
    BuildResult,
    build_repo as exec_build,
)
from .exec.init_dialog import (
    InitDialogDefaults,
    apply_language_selection as exec_apply_language_selection,
    detect_languages as exec_detect_languages,
    supported_languages as exec_supported_languages,
)
from .exec.repo import (
    RebuildResult,
    StatusResult,
    clean_repo as exec_clean,
    init_repo as exec_init,
    rebuild_repo as exec_rebuild,
    status_repo as exec_status,
)
from .policy import build as policy_build
from .policy import repo as policy_repo

logger = get_logger(__name__)


def init(repo_root: Optional[Path] = None) -> Path:
    logger.info("Initializing SCIONA repository.")
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_repo_has_commits(repo_state)
    return exec_init(repo_state)


def init_agents(repo_root: Optional[Path], *, mode: str = "append") -> Path:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_repo_has_commits(repo_state)
    return agents_runtime.upsert_agents_file(repo_state.repo_root, mode=mode)


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


def build(repo_root: Optional[Path] = None) -> BuildResult:
    logger.info("Building SCIONA snapshot.")
    repo_state = policy_repo.resolve_repo_state(repo_root)
    policy_repo.ensure_repo_has_commits(repo_state)
    policy = policy_build.resolve_build_policy(repo_state)
    policy_repo.ensure_clean_worktree_for_languages(repo_state, policy.analysis.languages)
    return _run_build(repo_state, policy)


def rebuild(repo_root: Optional[Path] = None) -> RebuildResult:
    logger.info("Rebuilding SCIONA repository.")
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_repo_has_commits(repo_state)
    policy_repo.ensure_clean_worktree_for_enabled_languages(repo_state)
    return exec_rebuild(repo_state)


def status(repo_root: Optional[Path] = None) -> StatusResult:
    logger.info("Fetching SCIONA status.")
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_initialized(repo_state)
    return exec_status(repo_state)


def clean(repo_root: Optional[Path] = None) -> bool:
    logger.info("Cleaning SCIONA repository state.")
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    return exec_clean(repo_state)


def clean_agents(repo_root: Optional[Path] = None) -> bool:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    return agents_runtime.remove_agents_block(repo_state.repo_root)


def _run_build(repo_state: RepoState, policy: BuildPolicy) -> BuildResult:
    policy_repo.ensure_initialized(repo_state)
    policy_repo.ensure_repo_has_commits(repo_state)
    ensure_prompts_initialized(repo_state.repo_root)
    return exec_build(repo_state, policy)
