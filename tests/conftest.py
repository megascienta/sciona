import importlib

import pytest
from typer.testing import CliRunner

from sciona.runtime import paths as runtime_paths
from sciona.pipelines.prompts import ensure_prompts_initialized

from tests.helpers import seed_repo_with_snapshot


@pytest.fixture
def repo_with_snapshot(tmp_path):
    return seed_repo_with_snapshot(tmp_path)


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def cli_app(repo_with_snapshot, monkeypatch):
    repo_root, _snapshot_id = repo_with_snapshot
    monkeypatch.setattr(runtime_paths, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    return cli_module.app


@pytest.fixture
def cli_app_with_prompts(repo_with_snapshot, monkeypatch):
    repo_root, _snapshot_id = repo_with_snapshot
    ensure_prompts_initialized(repo_root)
    monkeypatch.setattr(runtime_paths, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    return cli_module.app
