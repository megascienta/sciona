import importlib
import json

from typer.testing import CliRunner

from sciona.pipelines.config import public as config

from tests.helpers import seed_repo_with_snapshot


def test_cli_refs_outputs_json_matches(tmp_path, monkeypatch):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    monkeypatch.setattr(config, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    runner = CliRunner()

    result = runner.invoke(cli_module.app, ["refs", "pkg.alpha", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    refs_payload = payload["payload"]
    assert refs_payload["edges"]
