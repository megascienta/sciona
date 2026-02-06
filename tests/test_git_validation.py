import subprocess

import pytest

from sciona.runtime import git as git_ops
from sciona.runtime.git.exec import validate_repo_root
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


def test_run_git_allows_special_path_after_double_dash(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    path = repo_root / "weird[1].txt"
    path.write_text("ok", encoding="utf-8")
    output = git_ops.run_git(
        ["hash-object", "--no-filters", "--", path.name],
        repo_root,
    )
    assert output


def test_validate_repo_root_rejects_non_repo(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    with pytest.raises(GitError):
        validate_repo_root(repo_root)
