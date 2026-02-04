import importlib

from typer.testing import CliRunner

from sciona.runtime import paths as runtime_paths

from tests.helpers import seed_repo_with_snapshot


def test_cli_resolve_callable(tmp_path, monkeypatch):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    monkeypatch.setattr(runtime_paths, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    runner = CliRunner()

    result = runner.invoke(
        cli_module.app,
        ["resolve", "pkg.alpha.service.helper", "--kind", "callable"],
    )

    assert result.exit_code == 0
    assert "Resolved callable" in result.stdout
    assert "func_alpha" in result.stdout
