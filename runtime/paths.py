"""Runtime environment and repository helpers."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

from . import constants
from . import git as git_ops
from .errors import EnvError

def get_repo_root() -> Path:
    """Return the path to the git repository root for the current working dir."""
    try:
        return git_ops.get_repo_root()
    except git_ops.GitError as exc:
        raise EnvError("SCIONA must be run inside a git repository.") from exc


def ensure_repo_has_commits(repo_root: Path) -> None:
    """Ensure the repository has at least one commit."""
    try:
        git_ops.ensure_repo_has_commits(repo_root)
    except git_ops.GitError as exc:
        raise EnvError(str(exc)) from exc


def ensure_clean_worktree(repo_root: Path) -> None:
    """Abort if the working tree contains uncommitted changes."""
    try:
        git_ops.ensure_clean_worktree(repo_root)
    except git_ops.GitError as exc:
        raise EnvError(str(exc)) from exc


def is_worktree_dirty(repo_root: Path) -> bool:
    """Return True when the git working tree has uncommitted changes."""
    try:
        return git_ops.is_worktree_dirty(repo_root)
    except git_ops.GitError as exc:
        raise EnvError(str(exc)) from exc


def get_sciona_dir(repo_root: Path) -> Path:
    return repo_root / constants.SCIONA_DIR_NAME


def get_version_file(repo_root: Path) -> Path:
    return get_sciona_dir(repo_root) / constants.VERSION_FILENAME


def get_db_path(repo_root: Path) -> Path:
    return get_sciona_dir(repo_root) / constants.DB_FILENAME


def get_artifact_db_path(repo_root: Path) -> Path:
    return get_sciona_dir(repo_root) / constants.ARTIFACT_DB_FILENAME


def get_config_path(repo_root: Path) -> Path:
    return get_sciona_dir(repo_root) / constants.CONFIG_FILENAME


def get_prompts_dir(repo_root: Path) -> Path:
    return get_sciona_dir(repo_root) / constants.PROMPTS_DIRNAME


def get_prompts_registry_path(repo_root: Path) -> Path:
    return get_prompts_dir(repo_root) / constants.PROMPTS_REGISTRY_FILENAME


def get_log_dir(repo_root: Path) -> Path:
    if constants.LOG_DIRNAME:
        return get_sciona_dir(repo_root) / constants.LOG_DIRNAME
    return get_sciona_dir(repo_root)


def validate_repo_root(repo_root: Path) -> Path:
    try:
        resolved = repo_root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise EnvError(f"Invalid repo path: {repo_root}") from exc
    if not (resolved / ".git").exists():
        raise EnvError(f"{resolved} is not a git repository")
    sciona_dir = get_sciona_dir(resolved)
    try:
        sciona_dir.resolve().relative_to(resolved)
    except ValueError as exc:
        raise EnvError("Invalid .sciona path (path traversal detected)") from exc
    return resolved


def repo_name_prefix(repo_root: Path) -> str:
    """Return a sanitized repo name suitable for module prefixes."""
    name = _resolve_repo_name_root(repo_root).name or "repo"
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not cleaned:
        cleaned = "repo"
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned


def _resolve_repo_name_root(repo_root: Path) -> Path:
    git_path = Path(repo_root) / ".git"
    if not git_path.is_file():
        return Path(repo_root)
    try:
        content = git_path.read_text(encoding="utf-8").strip()
    except OSError:
        return Path(repo_root)
    if not content.startswith("gitdir:"):
        return Path(repo_root)
    gitdir_raw = content[len("gitdir:") :].strip()
    if not gitdir_raw:
        return Path(repo_root)
    gitdir = Path(gitdir_raw)
    if not gitdir.is_absolute():
        gitdir = (Path(repo_root) / gitdir).resolve()
    parts = gitdir.parts
    if ".git" in parts:
        git_index = parts.index(".git")
        if git_index > 0:
            return Path(*parts[:git_index])
    return Path(repo_root)
