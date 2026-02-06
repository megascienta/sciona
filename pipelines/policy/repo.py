"""Repository policy helpers (validation and guards)."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional, Set

from ...code_analysis.core.extract.registry import extensions_for_language
from ...runtime import git as git_ops
from ...runtime import paths as runtime_paths
from ...runtime import config as runtime_config
from ...runtime.git.adapter import GitAdapter, RealGitAdapter
from ..domain.repository import RepoState
from ...runtime.config import LanguageSettings
from ...runtime.config.defaults import LANGUAGE_DEFAULTS
from .. import setup as versioning
from ..errors import ConfigError, GitError


def resolve_repo_state(
    repo_root: Optional[Path] = None,
    *,
    git: Optional[GitAdapter] = None,
    allow_missing_config: bool = False,
) -> RepoState:
    git_adapter = git or RealGitAdapter()
    root = repo_root or runtime_paths.get_repo_root()
    return RepoState.from_repo_root(
        root,
        git=git_adapter,
        load_config=not allow_missing_config,
        allow_missing_config=allow_missing_config,
    )


def ensure_initialized(repo_state: RepoState) -> None:
    sciona_dir = repo_state.sciona_dir
    if not sciona_dir.exists():
        raise ConfigError(
            "SCIONA has not been initialized here.",
            code="not_initialized",
            hint="Run `sciona init` in the repository root.",
        )
    version_info = versioning.read_version_file(sciona_dir)
    versioning.ensure_schema_version(version_info, repo_state.repo_root)


def require_repo_root(*, allow_missing_config: bool = True) -> Path:
    repo_state = resolve_repo_state(allow_missing_config=allow_missing_config)
    ensure_initialized(repo_state)
    return repo_state.repo_root


def ensure_repo_has_commits(repo_state: RepoState) -> None:
    repo_state.git.ensure_repo_has_commits(repo_state.repo_root)


def ensure_clean_worktree(repo_state: RepoState) -> None:
    repo_state.git.ensure_clean_worktree(repo_state.repo_root)


def ensure_clean_worktree_for_languages(
    repo_state: RepoState,
    languages: Mapping[str, LanguageSettings],
) -> None:
    language_exts = _language_extensions(languages)
    dirty_paths = _dirty_language_paths(repo_state.repo_root, language_exts)
    if dirty_paths:
        raise GitError(
            "Uncommitted changes detected in tracked language sources. "
            "Please commit or stash before running SCIONA."
        )


def ensure_clean_worktree_for_enabled_languages(repo_state: RepoState) -> None:
    try:
        runtime_cfg = runtime_config.load_runtime_config(repo_state.repo_root)
    except ConfigError:
        language_exts = _all_language_extensions()
        dirty_paths = _dirty_language_paths(repo_state.repo_root, language_exts)
        if dirty_paths:
            raise GitError(
                "Uncommitted changes detected in tracked language sources. "
                "Please commit or stash before running SCIONA."
            )
        return
    ensure_clean_worktree_for_languages(repo_state, runtime_cfg.languages)


def dirty_worktree_warning(repo_state: RepoState) -> str | None:
    warning = (
        "Warning: worktree is dirty; outputs reflect the last committed snapshot, "
        "not current files."
    )
    try:
        runtime_cfg = runtime_config.load_runtime_config(repo_state.repo_root)
    except ConfigError:
        language_exts = _all_language_extensions()
        dirty_paths = _dirty_language_paths(repo_state.repo_root, language_exts)
        return warning if dirty_paths else None
    if is_worktree_dirty_for_languages(repo_state, runtime_cfg.languages):
        return warning
    return None


def _all_language_extensions() -> Set[str]:
    extensions: Set[str] = set()
    for name in LANGUAGE_DEFAULTS:
        extensions.update(ext.lower() for ext in extensions_for_language(name))
    return extensions


def is_worktree_dirty(repo_state: RepoState) -> bool:
    return repo_state.git.is_worktree_dirty(repo_state.repo_root)


def is_worktree_dirty_for_languages(
    repo_state: RepoState,
    languages: Mapping[str, LanguageSettings],
) -> bool:
    language_exts = _language_extensions(languages)
    return bool(_dirty_language_paths(repo_state.repo_root, language_exts))


def _language_extensions(languages: Mapping[str, LanguageSettings]) -> Set[str]:
    extensions: Set[str] = set()
    for name, lang_settings in languages.items():
        if not lang_settings.enabled:
            continue
        extensions.update(ext.lower() for ext in extensions_for_language(name))
    return extensions


def _dirty_language_paths(repo_root: Path, language_exts: Set[str]) -> list[Path]:
    if not language_exts:
        return []
    tracked = git_ops.tracked_paths(repo_root)
    dirty: list[Path] = []
    for path_text in git_ops.worktree_status_paths(repo_root):
        rel_path = Path(path_text)
        if rel_path.as_posix() not in tracked:
            continue
        if rel_path.suffix.lower() in language_exts:
            dirty.append(rel_path)
    return dirty


__all__ = [
    "ensure_clean_worktree",
    "ensure_clean_worktree_for_languages",
    "ensure_clean_worktree_for_enabled_languages",
    "ensure_initialized",
    "ensure_repo_has_commits",
    "is_worktree_dirty",
    "is_worktree_dirty_for_languages",
    "dirty_worktree_warning",
    "resolve_repo_state",
    "require_repo_root",
]
