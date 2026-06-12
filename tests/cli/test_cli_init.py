# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import importlib
from pathlib import Path

import pytest
import yaml

from sciona.runtime import paths as runtime_paths

from tests.helpers import commit_all, init_git_repo


def _make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    for relative_path, content in files.items():
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    commit_all(repo_root)
    return repo_root


def _make_app(repo_root: Path, monkeypatch):
    monkeypatch.setattr(runtime_paths, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    return cli_module.app


def _load_languages(repo_root: Path) -> dict:
    config_path = repo_root / ".sciona" / "config.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return data["languages"]


@pytest.fixture
def python_repo(tmp_path):
    return _make_repo(tmp_path, {"app.py": "print('hi')\n"})


def test_init_no_interactive_enables_detected_languages(
    python_repo, cli_runner, monkeypatch
):
    app = _make_app(python_repo, monkeypatch)
    result = cli_runner.invoke(app, ["init", "--no-interactive"])
    assert result.exit_code == 0
    languages = _load_languages(python_repo)
    assert languages["python"]["enabled"] is True
    assert languages["typescript"]["enabled"] is False
    assert languages["javascript"]["enabled"] is False
    assert languages["java"]["enabled"] is False
    assert "Enabled languages: python" in result.output
    assert "Edit .sciona/config.yaml" not in result.output


def test_init_no_interactive_config_is_buildable(
    python_repo, cli_runner, monkeypatch
):
    app = _make_app(python_repo, monkeypatch)
    result = cli_runner.invoke(app, ["init", "--no-interactive"])
    assert result.exit_code == 0
    build_result = cli_runner.invoke(app, ["build"])
    assert build_result.exit_code == 0


def test_init_languages_flag_overrides_detection(
    python_repo, cli_runner, monkeypatch
):
    app = _make_app(python_repo, monkeypatch)
    result = cli_runner.invoke(
        app, ["init", "--no-interactive", "--languages", "typescript"]
    )
    assert result.exit_code == 0
    languages = _load_languages(python_repo)
    assert languages["typescript"]["enabled"] is True
    assert languages["python"]["enabled"] is False
    assert "Enabled languages: typescript" in result.output


def test_init_languages_flag_rejects_unknown_language(
    python_repo, cli_runner, monkeypatch
):
    app = _make_app(python_repo, monkeypatch)
    result = cli_runner.invoke(
        app, ["init", "--no-interactive", "--languages", "cobol"]
    )
    assert result.exit_code != 0
    assert "Unknown language(s): cobol" in result.stderr
    assert "Supported:" in result.stderr
    assert not (python_repo / ".sciona").exists()


@pytest.mark.parametrize(
    "args",
    [
        ["--languages", "python"],
        ["--agents"],
        ["--claude"],
        ["--post-commit-hook"],
    ],
)
def test_init_flags_require_no_interactive(
    python_repo, cli_runner, monkeypatch, args
):
    app = _make_app(python_repo, monkeypatch)
    result = cli_runner.invoke(app, ["init", *args])
    assert result.exit_code != 0
    assert "require(s) --no-interactive" in result.stderr
    assert not (python_repo / ".sciona").exists()


def test_init_no_interactive_without_detected_languages(
    tmp_path, cli_runner, monkeypatch
):
    repo_root = _make_repo(tmp_path, {"notes.txt": "hello\n"})
    app = _make_app(repo_root, monkeypatch)
    result = cli_runner.invoke(app, ["init", "--no-interactive"])
    assert result.exit_code == 0
    languages = _load_languages(repo_root)
    assert all(entry["enabled"] is False for entry in languages.values())
    assert "No languages detected" in result.output
    assert "Edit .sciona/config.yaml" in result.output


def test_init_non_tty_without_flags_keeps_manual_guidance(
    python_repo, cli_runner, monkeypatch
):
    app = _make_app(python_repo, monkeypatch)
    result = cli_runner.invoke(app, ["init"])
    assert result.exit_code == 0
    languages = _load_languages(python_repo)
    assert all(entry["enabled"] is False for entry in languages.values())
    assert "Edit .sciona/config.yaml" in result.output
    assert "stdin is not a tty" in result.output
