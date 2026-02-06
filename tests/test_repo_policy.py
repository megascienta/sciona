import subprocess

import pytest

from sciona.pipelines.domain.repository import RepoState
from sciona.pipelines.policy import repo as repo_policy
from sciona.runtime.config import LanguageSettings
from sciona.runtime.errors import GitError


def _git(repo_root, *args):
    subprocess.run(
        ["git", *args], cwd=repo_root, check=True, capture_output=True, text=True
    )


def _init_repo(repo_root):
    _git(repo_root, "init")


def test_ensure_clean_worktree_for_languages_ignores_unrelated_extensions(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    path = repo_root / "note.txt"
    path.write_text("one", encoding="utf-8")
    _git(repo_root, "add", path.name)
    path.write_text("two", encoding="utf-8")

    repo_state = RepoState.from_repo_root(repo_root, allow_missing_config=True)
    languages = {"python": LanguageSettings(name="python", enabled=True)}

    repo_policy.ensure_clean_worktree_for_languages(repo_state, languages)


def test_ensure_clean_worktree_for_languages_detects_dirty_tracked(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    path = repo_root / "main.py"
    path.write_text("print('a')", encoding="utf-8")
    _git(repo_root, "add", path.name)
    path.write_text("print('b')", encoding="utf-8")

    repo_state = RepoState.from_repo_root(repo_root, allow_missing_config=True)
    languages = {"python": LanguageSettings(name="python", enabled=True)}

    with pytest.raises(GitError):
        repo_policy.ensure_clean_worktree_for_languages(repo_state, languages)
