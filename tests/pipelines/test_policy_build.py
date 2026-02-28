# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.pipelines.domain.repository import RepoState
from sciona.pipelines.policy import build as policy_build
from sciona.runtime.config import io as config_io
from sciona.runtime import constants as setup_config
from tests.helpers import init_git_repo


def _write_config(repo_root: Path) -> None:
    sciona_dir = repo_root / setup_config.SCIONA_DIR_NAME
    sciona_dir.mkdir(exist_ok=True)
    config_io.write_config_text(
        repo_root,
        """languages:\n  python:\n    enabled: true\n\ndiscovery:\n  exclude_globs: []\n""",
    )


def test_resolve_build_policy_uses_repo_config(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root, commit=True)
    _write_config(repo_root)

    repo_state = RepoState.from_repo_root(repo_root)
    policy = policy_build.resolve_build_policy(
        repo_state, refresh_artifacts=False, refresh_calls=False
    )

    assert policy.analysis.languages["python"].enabled is True
    assert policy.artifacts.refresh_artifacts is False
    assert policy.artifacts.refresh_calls is False
    assert policy.force_rebuild is False


def test_resolve_build_policy_can_force_rebuild(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root, commit=True)
    _write_config(repo_root)

    repo_state = RepoState.from_repo_root(repo_root)
    policy = policy_build.resolve_build_policy(
        repo_state,
        refresh_artifacts=False,
        refresh_calls=False,
        force_rebuild=True,
    )

    assert policy.force_rebuild is True
