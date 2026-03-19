# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

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
