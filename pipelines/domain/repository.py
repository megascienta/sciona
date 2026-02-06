"""Repository state container for orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ...runtime import paths as runtime
from ...runtime.config import ScionaConfig, load_sciona_config
from ...runtime.git.adapter import GitAdapter, GitCliAdapter


@dataclass(frozen=True)
class RepoState:
    repo_root: Path
    sciona_dir: Path
    db_path: Path
    artifact_db_path: Path
    config: Optional[ScionaConfig]
    git: GitAdapter

    @staticmethod
    def from_repo_root(
        repo_root: Path,
        *,
        git: Optional[GitAdapter] = None,
        load_config: bool = True,
        allow_missing_config: bool = False,
    ) -> "RepoState":
        git_adapter = git or GitCliAdapter()
        repo_root = runtime.validate_repo_root(repo_root)
        sciona_dir = runtime.get_sciona_dir(repo_root)
        config: Optional[ScionaConfig] = None
        if load_config:
            try:
                config = load_sciona_config(repo_root)
            except Exception:
                if not allow_missing_config:
                    raise
        return RepoState(
            repo_root=repo_root,
            sciona_dir=sciona_dir,
            db_path=runtime.get_db_path(repo_root),
            artifact_db_path=runtime.get_artifact_db_path(repo_root),
            config=config,
            git=git_adapter,
        )


__all__ = ["RepoState"]
