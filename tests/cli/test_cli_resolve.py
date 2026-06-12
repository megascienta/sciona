# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json

from sciona.runtime import paths as runtime_paths


def test_cli_resolve_callable(cli_app, cli_runner):
    prefix = runtime_paths.repo_name_prefix(runtime_paths.get_repo_root())
    result = cli_runner.invoke(
        cli_app,
        ["resolve", f"{prefix}.pkg.alpha.service.helper", "--kind", "callable"],
    )

    assert result.exit_code == 0
    assert "Resolved callable" in result.stdout
    assert "func_alpha" in result.stdout


def test_cli_resolve_without_kind(cli_app, cli_runner):
    prefix = runtime_paths.repo_name_prefix(runtime_paths.get_repo_root())
    result = cli_runner.invoke(
        cli_app,
        ["resolve", f"{prefix}.pkg.alpha.service.helper"],
    )

    assert result.exit_code == 0
    assert "Resolved identifier" in result.stdout
    assert "func_alpha" in result.stdout


def test_cli_resolve_auto_resolve_human_output(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app,
        ["resolve", "helper", "--kind", "callable"],
    )

    assert result.exit_code == 0
    assert "func_alpha" in result.stdout
    assert "auto-resolved from 'helper'" in result.stdout


def test_cli_resolve_auto_resolve_json(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app,
        ["resolve", "helper", "--kind", "callable", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "resolved"
    assert payload["resolved_id"] == "func_alpha"
    assert payload["resolved_from"] == "helper"
