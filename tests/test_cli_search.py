import importlib
import json

from typer.testing import CliRunner

from sciona.pipelines.config import public as config

from tests.helpers import seed_repo_with_snapshot


def test_cli_search_outputs_json_matches(tmp_path, monkeypatch):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    monkeypatch.setattr(config, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    runner = CliRunner()

    result = runner.invoke(cli_module.app, ["search", "pkg.alpha", "--kind", "module", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["query"] == "pkg.alpha"
    assert payload["matches"]


def test_cli_search_allows_any_kind(tmp_path, monkeypatch):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    monkeypatch.setattr(config, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    runner = CliRunner()

    result = runner.invoke(cli_module.app, ["search", "pkg.alpha", "--kind", "any", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["matches"]
