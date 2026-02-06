# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json


def test_cli_refs_outputs_json_matches(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ["refs", "pkg.alpha", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    refs_payload = payload["payload"]
    assert refs_payload["edges"]
