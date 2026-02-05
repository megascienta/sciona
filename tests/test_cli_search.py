import json


def test_cli_search_outputs_json_matches(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ["search", "pkg.alpha", "--kind", "module", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["query"] == "pkg.alpha"
    assert payload["matches"]


def test_cli_search_allows_any_kind(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ["search", "pkg.alpha", "--kind", "any", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["matches"]
