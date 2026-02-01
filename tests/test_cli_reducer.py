import importlib
import json

from typer.testing import CliRunner

from sciona.pipelines.config import public as config

from tests.helpers import seed_repo_with_snapshot


def test_cli_reducer_renders_payload(tmp_path, monkeypatch):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    monkeypatch.setattr(config, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    runner = CliRunner()

    result = runner.invoke(cli_module.app, ["reducer", "--id", "structural_index"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "payload" in payload


def test_cli_reducer_callable_id_resolves_method(tmp_path, monkeypatch):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    monkeypatch.setattr(config, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    runner = CliRunner()

    result = runner.invoke(
        cli_module.app,
        ["reducer", "--id", "callable_overview", "--callable-id", "pkg.alpha.Service.run"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    reducer_payload = json.loads(_strip_json_fence(payload["payload"]))
    assert reducer_payload["callable_id"] == "meth_alpha"


def test_cli_reducer_list_outputs_calls(tmp_path, monkeypatch):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    monkeypatch.setattr(config, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    runner = CliRunner()

    result = runner.invoke(cli_module.app, ["reducer", "list"])

    assert result.exit_code == 0
    assert "reducer --id structural_index" in result.stdout


def _strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```json") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        return "\n".join(lines[1:-1])
    return trimmed
