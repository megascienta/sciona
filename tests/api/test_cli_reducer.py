# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json

from sciona.runtime import paths as runtime_paths


def test_cli_reducer_renders_payload(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ["reducer", "--id", "structural_index"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "payload" in payload


def test_cli_reducer_callable_id_resolves_method(cli_app, cli_runner):
    prefix = runtime_paths.repo_name_prefix(runtime_paths.get_repo_root())
    result = cli_runner.invoke(
        cli_app,
        [
            "reducer",
            "--id",
            "callable_overview",
            "--callable-id",
            f"{prefix}.pkg.alpha.Service.run",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    reducer_payload = json.loads(_strip_json_fence(payload["payload"]))
    assert reducer_payload["callable_id"] == "meth_alpha"


def test_cli_reducer_list_outputs_calls(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ["reducer", "list"])

    assert result.exit_code == 0
    assert "reducer --id structural_index" in result.stdout


def _strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```json") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        return "\n".join(lines[1:-1])
    return trimmed
