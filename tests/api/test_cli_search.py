# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json

from sciona.runtime import paths as runtime_paths


def test_cli_search_outputs_json_matches(cli_app, cli_runner):
    prefix = runtime_paths.repo_name_prefix(runtime_paths.get_repo_root())
    result = cli_runner.invoke(
        cli_app, ["search", f"{prefix}.pkg.alpha", "--kind", "module", "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["query"] == f"{prefix}.pkg.alpha"
    assert payload["matches"]


def test_cli_search_allows_any_kind(cli_app, cli_runner):
    prefix = runtime_paths.repo_name_prefix(runtime_paths.get_repo_root())
    result = cli_runner.invoke(
        cli_app, ["search", f"{prefix}.pkg.alpha", "--kind", "any", "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["matches"]
