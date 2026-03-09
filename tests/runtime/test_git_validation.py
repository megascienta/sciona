# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import subprocess
from pathlib import Path

import pytest

from sciona.runtime import git as git_ops
from sciona.runtime.git.exec import validate_git_args, validate_repo_root
from sciona.runtime.errors import GitError
from sciona.runtime.git import ops as git_ops_module
from tests.helpers import init_git_repo, write_and_commit_file


def test_run_git_rejects_dangerous_args(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    with pytest.raises(GitError):
        git_ops.run_git(["status;rm -rf /"], repo_root)


def test_run_git_accepts_safe_args(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    output = git_ops.run_git(["--version"], repo_root)
    assert "git version" in output.lower()


def test_validate_git_args_allows_ls_files_z() -> None:
    validate_git_args(["ls-files", "-z"])


def test_run_git_allows_special_path_after_double_dash(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
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


def test_merge_base_returns_common_ancestor(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    write_and_commit_file(repo_root, "base.txt", "base\n", message="base")
    default_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    base_sha = git_ops.head_sha(repo_root).strip()

    subprocess.run(
        ["git", "checkout", "-b", "feature"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    write_and_commit_file(repo_root, "feature.txt", "feature\n", message="feature")
    feature_sha = git_ops.head_sha(repo_root).strip()

    subprocess.run(
        ["git", "checkout", default_branch],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    write_and_commit_file(repo_root, "main.txt", "main\n", message="main")
    main_sha = git_ops.head_sha(repo_root).strip()

    merge_base_sha = git_ops.merge_base(repo_root, feature_sha, main_sha).strip()
    assert merge_base_sha == base_sha


def test_worktree_status_paths_parses_rename_and_copy(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)

    status_output = "R  old.py\x00new.py\x00C  src.py\x00copy.py\x00M  keep.py\x00?? new.txt\x00"

    def _fake_run_git_cached(*_args, **_kwargs):
        return status_output

    monkeypatch.setattr(git_ops_module, "_run_git_cached", _fake_run_git_cached)
    assert git_ops.worktree_status_paths(repo_root) == [
        "old.py",
        "new.py",
        "src.py",
        "copy.py",
        "keep.py",
        "new.txt",
    ]


def test_worktree_status_tracked_paths_excludes_untracked(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)

    status_output = "M  tracked.py\x00?? untracked.py\x00R  old.py\x00new.py\x00"

    def _fake_run_git_cached(*_args, **_kwargs):
        return status_output

    monkeypatch.setattr(git_ops_module, "_run_git_cached", _fake_run_git_cached)
    assert git_ops.worktree_status_tracked_paths(repo_root) == {
        "tracked.py",
        "old.py",
        "new.py",
    }


def test_diff_name_status_parses_expected_rows(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)

    diff_output = "M\tchanged.py\nR100\told.py\tnew.py\nC100\ta.py\tb.py\n"

    def _fake_run_git_cached(*_args, **_kwargs):
        return diff_output

    monkeypatch.setattr(git_ops_module, "_run_git_cached", _fake_run_git_cached)
    assert git_ops.diff_name_status(repo_root, "base") == [
        ("M", ["changed.py"]),
        ("R100", ["old.py", "new.py"]),
        ("C100", ["a.py", "b.py"]),
    ]


def test_submodule_paths_extracts_mode_160000(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)

    stage_output = (
        "100644 abcdef 0\tregular.py\n"
        "160000 123456 0\tsubmods/engine\n"
        "160000 fedcba 0\tsubmods/tools\n"
    )

    def _fake_run_git_cached(*_args, **_kwargs):
        return stage_output

    monkeypatch.setattr(git_ops_module, "_run_git_cached", _fake_run_git_cached)
    assert git_ops.submodule_paths(repo_root) == {"submods/engine", "submods/tools"}


def test_blob_sha_batch_rejects_newline_in_path(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    write_and_commit_file(repo_root, "seed.txt", "seed\n", message="seed")
    with pytest.raises(GitError, match="Invalid path for git hash"):
        git_ops.blob_sha_batch(repo_root, [Path("bad\nname.py")])


def test_tracked_paths_parses_nul_delimited_git_output(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)

    def _fake_run_git(args, *_args, **_kwargs):
        if args == ["--version"]:
            return "git version 2.x"
        assert args == ["ls-files", "-z"]
        return "pkg/a.py\x00pkg/b.py\x00"

    monkeypatch.setattr(git_ops_module, "run_git", _fake_run_git)
    assert git_ops.tracked_paths(repo_root) == {"pkg/a.py", "pkg/b.py"}


@pytest.mark.parametrize("bad_path", [Path("/tmp/abs.py"), Path("../escape.py")])
def test_blob_sha_rejects_non_repo_relative_paths(tmp_path, bad_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    write_and_commit_file(repo_root, "seed.txt", "seed\n", message="seed")

    with pytest.raises(GitError, match="Invalid path for git hash"):
        git_ops.blob_sha(repo_root, bad_path)


@pytest.mark.parametrize("bad_path", [Path("/tmp/abs.py"), Path("../escape.py")])
def test_blob_sha_batch_rejects_non_repo_relative_paths(tmp_path, bad_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    write_and_commit_file(repo_root, "seed.txt", "seed\n", message="seed")

    with pytest.raises(GitError, match="Invalid path for git hash"):
        git_ops.blob_sha_batch(repo_root, [bad_path])
