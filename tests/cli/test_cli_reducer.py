# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json

from sciona.runtime import paths as runtime_paths
from sciona.runtime.errors import EnvError
from tests.helpers import init_git_repo, parse_json_payload


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
    reducer_payload = parse_json_payload(payload["payload"])
    assert reducer_payload["callable_id"] == "meth_alpha"


def test_cli_reducer_callable_id_auto_resolves_with_note(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app,
        [
            "reducer",
            "--id",
            "callable_overview",
            "--callable-id",
            "helper",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    reducer_payload = parse_json_payload(payload["payload"])
    assert reducer_payload["callable_id"] == "func_alpha"
    assert payload["args"]["callable_id"] == "func_alpha"
    assert any(
        note.startswith("[resolution] callable_id 'helper' auto-resolved")
        for note in payload["notes"]
    )


def test_cli_reducer_dependency_edges_accepts_package_prefix_scope(cli_app, cli_runner):
    prefix = runtime_paths.repo_name_prefix(runtime_paths.get_repo_root())
    result = cli_runner.invoke(
        cli_app,
        [
            "reducer",
            "--id",
            "dependency_edges",
            "--module-id",
            f"{prefix}.pkg",
            "--compact",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    reducer_payload = parse_json_payload(payload["payload"])
    assert payload["args"]["module_id"] == f"{prefix}.pkg"
    assert reducer_payload["module_scope"]["scope_kind"] == "package_prefix"
    assert reducer_payload["module_scope"]["scope_filter"] == f"{prefix}.pkg"
    assert reducer_payload["edge_count"] > 0


def test_cli_reducer_ownership_summary_accepts_package_prefix_scope(cli_app, cli_runner):
    prefix = runtime_paths.repo_name_prefix(runtime_paths.get_repo_root())
    result = cli_runner.invoke(
        cli_app,
        [
            "reducer",
            "--id",
            "ownership_summary",
            "--module-id",
            f"{prefix}.pkg",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    reducer_payload = parse_json_payload(payload["payload"])
    assert payload["args"]["module_id"] == f"{prefix}.pkg"
    assert reducer_payload["scope_kind"] == "package_prefix"
    assert reducer_payload["scope_filter"] == f"{prefix}.pkg"
    assert "module_structural_id" not in reducer_payload
    assert reducer_payload["submodules"]["entries"]


def test_cli_reducer_bare_compact_flag_enables_compact_mode(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app, ["reducer", "--id", "structural_index", "--compact"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["args"]["compact"] is True
    reducer_payload = parse_json_payload(payload["payload"])
    assert reducer_payload["payload_kind"] == "compact_summary"


def test_cli_reducer_compact_accepts_explicit_values(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app, ["reducer", "--id", "structural_index", "--compact", "true"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["args"]["compact"] is True

    result = cli_runner.invoke(
        cli_app, ["reducer", "--id", "structural_index", "--compact", "false"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["args"]["compact"] is False
    reducer_payload = parse_json_payload(payload["payload"])
    assert reducer_payload.get("payload_kind") != "compact_summary"


def test_cli_reducer_rejects_non_boolean_compact_value(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app, ["reducer", "--id", "structural_index", "--compact", "maybe"]
    )

    assert result.exit_code != 0


def test_cli_reducer_list_outputs_calls(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ["reducer", "list"])

    assert result.exit_code == 0
    assert "reducer --id structural_index" in result.stdout
    assert "[--compact]" in result.stdout
    assert "--compact COMPACT" not in result.stdout
    assert "--function-id" not in result.stdout
    assert "--method-id" not in result.stdout
    assert "reducer --id callable_source --callable-id CALLABLE_ID" in result.stdout
    assert "--id symbol_lookup --query QUERY" in result.stdout


def test_cli_reducer_list_works_outside_git_repo(cli_app, cli_runner, monkeypatch):
    def _raise_env_error():
        raise EnvError("SCIONA must be run inside a git repository.")

    monkeypatch.setattr(runtime_paths, "get_repo_root", _raise_env_error)

    result = cli_runner.invoke(cli_app, ["reducer", "list"])

    assert result.exit_code == 0
    assert "Not inside a git repository" in result.stdout
    assert "reducer --id structural_index" in result.stdout


def test_cli_reducer_info_works_outside_git_repo(cli_app, cli_runner, monkeypatch):
    def _raise_env_error():
        raise EnvError("SCIONA must be run inside a git repository.")

    monkeypatch.setattr(runtime_paths, "get_repo_root", _raise_env_error)

    result = cli_runner.invoke(cli_app, ["reducer", "info", "--id", "structural_index"])

    assert result.exit_code == 0
    assert "Not inside a git repository" in result.stdout
    assert "Reducer: structural_index" in result.stdout


def test_cli_reducer_list_json_outside_git_repo_keeps_stdout_clean(
    cli_app, cli_runner, monkeypatch
):
    def _raise_env_error():
        raise EnvError("SCIONA must be run inside a git repository.")

    monkeypatch.setattr(runtime_paths, "get_repo_root", _raise_env_error)

    result = cli_runner.invoke(cli_app, ["reducer", "list", "--json"])

    assert result.exit_code == 0
    entries = json.loads(result.stdout)
    reducer_ids = {entry["reducer_id"] for entry in entries}
    assert "structural_index" in reducer_ids
    assert "Not inside a git repository" in result.stderr


def test_cli_reducer_info_json_outside_git_repo_keeps_stdout_clean(
    cli_app, cli_runner, monkeypatch
):
    def _raise_env_error():
        raise EnvError("SCIONA must be run inside a git repository.")

    monkeypatch.setattr(runtime_paths, "get_repo_root", _raise_env_error)

    result = cli_runner.invoke(
        cli_app, ["reducer", "info", "--id", "structural_index", "--json"]
    )

    assert result.exit_code == 0
    entry = json.loads(result.stdout)
    assert entry["reducer_id"] == "structural_index"
    assert "Not inside a git repository" in result.stderr


def test_cli_reducer_list_works_without_init(cli_app, cli_runner, monkeypatch, tmp_path):
    repo_root = tmp_path / "uninitialized_repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    monkeypatch.setattr(runtime_paths, "get_repo_root", lambda: repo_root)

    result = cli_runner.invoke(cli_app, ["reducer", "list"])

    assert result.exit_code == 0
    assert "has not been initialized" in result.stdout
    assert "reducer --id structural_index" in result.stdout


def test_cli_reducer_json_without_init_keeps_stdout_clean(
    cli_app, cli_runner, monkeypatch, tmp_path
):
    repo_root = tmp_path / "uninitialized_repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    monkeypatch.setattr(runtime_paths, "get_repo_root", lambda: repo_root)

    list_result = cli_runner.invoke(cli_app, ["reducer", "list", "--json"])

    assert list_result.exit_code == 0
    entries = json.loads(list_result.stdout)
    reducer_ids = {entry["reducer_id"] for entry in entries}
    assert "structural_index" in reducer_ids
    assert "has not been initialized" in list_result.stderr

    info_result = cli_runner.invoke(
        cli_app, ["reducer", "info", "--id", "structural_index", "--json"]
    )

    assert info_result.exit_code == 0
    entry = json.loads(info_result.stdout)
    assert entry["reducer_id"] == "structural_index"
    assert "has not been initialized" in info_result.stderr


def test_cli_reducer_json_flag_is_noop(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app, ["reducer", "--id", "structural_index", "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["reducer_id"] == "structural_index"


def test_cli_reducer_info_json_outputs_machine_readable(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app, ["reducer", "info", "--id", "structural_index", "--json"]
    )

    assert result.exit_code == 0
    entry = json.loads(result.stdout)
    assert entry["reducer_id"] == "structural_index"
    assert entry["category"] == "orientation"


def test_cli_reducer_info_json_without_id_lists_all(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ["reducer", "info", "--json"])

    assert result.exit_code == 0
    entries = json.loads(result.stdout)
    reducer_ids = {entry["reducer_id"] for entry in entries}
    assert "structural_index" in reducer_ids


def test_cli_reducer_list_json_outputs_machine_readable(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app, ["reducer", "list", "--id", "structural_index", "--json"]
    )

    assert result.exit_code == 0
    entries = json.loads(result.stdout)
    assert len(entries) == 1
    assert entries[0]["reducer_id"] == "structural_index"
