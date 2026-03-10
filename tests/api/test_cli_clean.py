# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.api import cli as api_cli
from sciona.pipelines import hooks
from sciona.runtime.agents import setup as agents
from sciona.reducers.registry import get_reducers


def _post_commit_hook_path(repo_root: Path) -> Path:
    return repo_root / ".git" / "hooks" / "post-commit"


def test_cli_clean_removes_sciona_hook_and_appended_agents(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _ = repo_with_snapshot
    monkeypatch.setattr(api_cli, "get_repo_root", lambda: repo_root)
    hook_status = hooks.install_post_commit_hook(repo_root, "sciona build")
    assert hook_status.installed is True

    target = repo_root / agents.AGENTS_FILENAME
    target.write_text("Custom header\n", encoding="utf-8")
    agents.upsert_agents_file(repo_root, mode="append", reducers=get_reducers())
    assert target.exists()

    result = cli_runner.invoke(cli_app, ["clean"])
    assert result.exit_code == 0
    assert not (repo_root / ".sciona").exists()

    post_commit = _post_commit_hook_path(repo_root)
    if post_commit.exists():
        text = post_commit.read_text(encoding="utf-8")
        assert "# sciona:begin" not in text
        assert "# sciona:end" not in text
    assert hooks.post_commit_hook_status(repo_root).installed is False

    assert target.exists()
    cleaned_agents = target.read_text(encoding="utf-8")
    assert "Custom header" in cleaned_agents
    assert agents.BEGIN_MARKER not in cleaned_agents
    assert agents.END_MARKER not in cleaned_agents


def test_cli_clean_removes_sciona_owned_agents_file(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _ = repo_with_snapshot
    monkeypatch.setattr(api_cli, "get_repo_root", lambda: repo_root)

    target = repo_root / agents.AGENTS_FILENAME
    agents.upsert_agents_file(repo_root, mode="overwrite", reducers=get_reducers())
    assert target.exists()

    result = cli_runner.invoke(cli_app, ["clean"])
    assert result.exit_code == 0
    assert not target.exists()
