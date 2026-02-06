import subprocess

import pytest

from sciona.runtime import git as git_ops
from sciona.runtime.errors import GitError


def _init_repo(repo_root):
    subprocess.run(
        ["git", "init"], cwd=repo_root, check=True, capture_output=True, text=True
    )


def test_run_git_rejects_dangerous_args(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    with pytest.raises(GitError):
        git_ops.run_git(["status;rm -rf /"], repo_root)


def test_run_git_accepts_safe_args(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    output = git_ops.run_git(["--version"], repo_root)
    assert "git version" in output.lower()
