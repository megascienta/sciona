# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.pipelines import hooks
from tests.helpers import init_git_repo


def test_install_and_remove_post_commit_hook(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root, commit=True)

    status = hooks.install_post_commit_hook(repo_root, "sciona build")
    assert status.installed is True
    assert status.command == "sciona build"
    assert status.hook_path.exists()
    assert "sciona build" in status.hook_path.read_text(encoding="utf-8")

    current = hooks.post_commit_hook_status(repo_root)
    assert current.installed is True
    assert current.command == "sciona build"

    removed = hooks.remove_post_commit_hook(repo_root)
    assert removed.installed is False
    assert removed.hook_path.exists() is False
