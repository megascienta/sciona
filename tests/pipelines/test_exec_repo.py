# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

import pytest

from sciona.pipelines.domain.repository import RepoState
from sciona.pipelines.exec.repo import clean_repo
from sciona.pipelines.errors import ConfigError
from sciona.runtime.git.adapter import GitCliAdapter


def _repo_state(repo_root: Path, sciona_dir: Path) -> RepoState:
    return RepoState(
        repo_root=repo_root,
        sciona_dir=sciona_dir,
        db_path=repo_root / ".sciona" / "sciona.db",
        artifact_db_path=repo_root / ".sciona" / "sciona.artifacts.db",
        config=None,
        git=GitCliAdapter(),
    )


def test_clean_repo_rejects_non_canonical_sciona_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    rogue_dir = tmp_path / "rogue"
    rogue_dir.mkdir()

    with pytest.raises(ConfigError, match="non-canonical SCIONA directory"):
        clean_repo(_repo_state(repo_root, rogue_dir))


def test_clean_repo_rejects_symlinked_sciona_dir(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    expected = repo_root / ".sciona"
    rogue = tmp_path / "rogue"
    rogue.mkdir()
    expected.symlink_to(rogue)

    with pytest.raises(ConfigError, match="symlinked SCIONA directory"):
        clean_repo(_repo_state(repo_root, expected))
