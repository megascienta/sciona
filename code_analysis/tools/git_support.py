"""Git helper utilities for ingestion."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

from ...runtime.errors import GitError
from ...runtime import git as git_ops

def validate_git_repo(repo_root: Path) -> None:
    try:
        git_ops.ensure_repo(repo_root)
    except git_ops.GitError as exc:
        raise GitError(str(exc)) from exc


def tracked_paths(repo_root: Path) -> Set[str]:
    """Return the set of tracked file paths relative to the repo root."""
    validate_git_repo(repo_root)
    try:
        return git_ops.tracked_paths(repo_root)
    except git_ops.GitError as exc:
        raise GitError(str(exc)) from exc


def blob_sha(repo_root: Path, relative_path: Path) -> str:
    """Compute the git blob SHA for the given file from the working tree."""
    validate_git_repo(repo_root)
    try:
        return git_ops.blob_sha(repo_root, relative_path)
    except git_ops.GitError as exc:
        raise GitError(str(exc)) from exc


def blob_sha_batch(repo_root: Path, relative_paths: List[Path]) -> Dict[Path, str]:
    """Compute git blob SHAs for multiple files in one call."""
    validate_git_repo(repo_root)
    try:
        return git_ops.blob_sha_batch(repo_root, relative_paths)
    except git_ops.GitError as exc:
        raise GitError(str(exc)) from exc
