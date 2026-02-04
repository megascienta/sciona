import importlib
import json

from typer.testing import CliRunner

from sciona.runtime import paths as runtime_paths
from sciona.prompts.bootstrap import ensure_prompts_initialized

from tests.helpers import seed_repo_with_snapshot


def test_cli_prompt_json_includes_sections(tmp_path, monkeypatch):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    ensure_prompts_initialized(repo_root)
    monkeypatch.setattr(runtime_paths, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)
    runner = CliRunner()

    result = runner.invoke(
        cli_module.app,
        [
            "prompt",
            "run",
            "preflight_v1",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "prompt" in payload
    assert "prompt_header" in payload
    assert "prompt_body" in payload
    assert "instructions" in payload
    assert "evidence" in payload
    assert "resolved_arg_map" in payload
    assert "PROMPT:" in (payload["prompt_header"] or "")
    assert "SCIONA pre-flight" in (payload["prompt_body"] or "")
