"""Git repository and metadata helpers for SCIONA."""

from __future__ import annotations

from ..errors import GitError
from .exec import run_git
from .ops import (
    blob_sha,
    blob_sha_batch,
    commit_meta,
    diff_name_status,
    ensure_clean_worktree,
    ensure_repo,
    ensure_repo_has_commits,
    git_output,
    get_repo_root,
    ignored_tracked_paths,
    is_worktree_dirty,
    head_sha,
    merge_base,
    submodule_paths,
    tracked_paths,
    untracked_paths,
    worktree_status_paths,
)

__all__ = [
    "GitError",
    "blob_sha",
    "blob_sha_batch",
    "commit_meta",
    "diff_name_status",
    "ensure_repo",
    "ensure_repo_has_commits",
    "ensure_clean_worktree",
    "git_output",
    "get_repo_root",
    "ignored_tracked_paths",
    "is_worktree_dirty",
    "head_sha",
    "merge_base",
    "submodule_paths",
    "run_git",
    "tracked_paths",
    "untracked_paths",
    "worktree_status_paths",
]
