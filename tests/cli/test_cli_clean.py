# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.cli import repo_ops
from sciona.pipelines import hooks
from sciona.runtime.agents import setup as agents
from sciona.runtime.agents import claude_setup as claude
from sciona.runtime.agents import settings_setup as settings
from sciona.runtime.agents._block_utils import BEGIN_MARKER, END_MARKER
from sciona.reducers.registry import get_reducers


def _post_commit_hook_path(repo_root: Path) -> Path:
    return repo_root / ".git" / "hooks" / "post-commit"


def test_cli_clean_removes_sciona_hook_and_appended_agents(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _ = repo_with_snapshot
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)
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
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)

    target = repo_root / agents.AGENTS_FILENAME
    agents.upsert_agents_file(repo_root, mode="overwrite", reducers=get_reducers())
    assert target.exists()

    result = cli_runner.invoke(cli_app, ["clean"])
    assert result.exit_code == 0
    assert not target.exists()


def test_cli_clean_removes_appended_claude_block(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _ = repo_with_snapshot
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)

    target = repo_root / claude.CLAUDE_FILENAME
    target.write_text("Custom header\n", encoding="utf-8")
    claude.upsert_claude_file(repo_root, mode="append", reducers=get_reducers())
    assert target.exists()

    result = cli_runner.invoke(cli_app, ["clean"])
    assert result.exit_code == 0

    assert target.exists()
    cleaned = target.read_text(encoding="utf-8")
    assert "Custom header" in cleaned
    assert BEGIN_MARKER not in cleaned
    assert END_MARKER not in cleaned


def test_cli_clean_removes_sciona_owned_claude_file(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _ = repo_with_snapshot
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)

    target = repo_root / claude.CLAUDE_FILENAME
    claude.upsert_claude_file(repo_root, mode="overwrite", reducers=get_reducers())
    assert target.exists()

    result = cli_runner.invoke(cli_app, ["clean"])
    assert result.exit_code == 0
    assert not target.exists()


def test_cli_clean_no_claude_flag_skips_claude(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _ = repo_with_snapshot
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)

    target = repo_root / claude.CLAUDE_FILENAME
    claude.upsert_claude_file(repo_root, mode="overwrite", reducers=get_reducers())
    assert target.exists()

    result = cli_runner.invoke(cli_app, ["clean", "--no-claude"])
    assert result.exit_code == 0
    assert target.exists()
    assert BEGIN_MARKER in target.read_text(encoding="utf-8")


def test_cli_clean_removes_dot_claude_settings(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _ = repo_with_snapshot
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)

    settings.upsert_claude_settings(repo_root)
    target = repo_root / settings.CLAUDE_DIR / settings.SETTINGS_FILENAME
    assert target.exists()

    result = cli_runner.invoke(cli_app, ["clean"])
    assert result.exit_code == 0
    assert not target.exists()


def test_cli_clean_no_claude_flag_skips_settings(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _ = repo_with_snapshot
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)

    settings.upsert_claude_settings(repo_root)
    target = repo_root / settings.CLAUDE_DIR / settings.SETTINGS_FILENAME
    assert target.exists()

    result = cli_runner.invoke(cli_app, ["clean", "--no-claude"])
    assert result.exit_code == 0
    assert target.exists()


def test_cli_clean_command_surface_has_agents_and_claude_flags(cli_app):
    """Catch future drift: --agents and --claude must be present on sciona clean."""
    import typer

    click_app = typer.main.get_command(cli_app)
    clean_cmd = click_app.commands["clean"]
    all_opts = {
        opt
        for param in clean_cmd.params
        for opt in (list(param.opts) + list(getattr(param, "secondary_opts", [])))
    }
    assert "--agents" in all_opts, "--agents missing from sciona clean"
    assert "--no-agents" in all_opts, "--no-agents missing from sciona clean"
    assert "--claude" in all_opts, "--claude missing from sciona clean"
    assert "--no-claude" in all_opts, "--no-claude missing from sciona clean"
