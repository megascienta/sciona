"""Git adapter abstraction for test seams."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .. import paths as runtime


class GitAdapter(Protocol):
    def get_repo_root(self) -> Path: ...
    def ensure_repo_has_commits(self, repo_root: Path) -> None: ...
    def ensure_clean_worktree(self, repo_root: Path) -> None: ...
    def is_worktree_dirty(self, repo_root: Path) -> bool: ...


@dataclass(frozen=True)
class GitCliAdapter:
    def get_repo_root(self) -> Path:
        return runtime.get_repo_root()

    def ensure_repo_has_commits(self, repo_root: Path) -> None:
        runtime.ensure_repo_has_commits(repo_root)

    def ensure_clean_worktree(self, repo_root: Path) -> None:
        runtime.ensure_clean_worktree(repo_root)

    def is_worktree_dirty(self, repo_root: Path) -> bool:
        return runtime.is_worktree_dirty(repo_root)


__all__ = ["GitAdapter", "GitCliAdapter"]
