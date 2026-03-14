# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import importlib
import json

from sciona.cli import repo_ops
from sciona.cli.commands import register_build as build_command
from sciona.runtime import config as runtime_config
from sciona.runtime import paths as runtime_paths
from sciona.pipelines.exec.build import BuildResult

from tests.helpers import commit_all


def _fake_result() -> BuildResult:
    return BuildResult(
        files_processed=1,
        nodes_recorded=1,
        snapshot_id="snap",
        status="reused",
        enabled_languages=["python"],
        discovery_counts={"python": 1},
        discovery_candidates={"python": 1},
        discovery_excluded_by_glob={},
        discovery_excluded_total=0,
        exclude_globs=[],
        parse_failures=0,
        analysis_warnings=[],
        artifact_warnings=[],
    )


def _fake_committed_result() -> BuildResult:
    return BuildResult(
        files_processed=1,
        nodes_recorded=1,
        snapshot_id="snap",
        status="committed",
        enabled_languages=["python"],
        discovery_counts={"python": 1},
        discovery_candidates={"python": 1},
        discovery_excluded_by_glob={},
        discovery_excluded_total=0,
        exclude_globs=[],
        parse_failures=0,
        analysis_warnings=[],
        artifact_warnings=[],
    )


def _fake_degraded_result() -> BuildResult:
    return BuildResult(
        files_processed=1,
        nodes_recorded=1,
        snapshot_id="snap",
        status="committed",
        health="degraded",
        enabled_languages=["python"],
        discovery_counts={"python": 1},
        discovery_candidates={"python": 1},
        discovery_excluded_by_glob={},
        discovery_excluded_total=0,
        exclude_globs=[],
        parse_failures=1,
        analysis_warnings=[],
        artifact_warnings=[],
    )


def _fake_report() -> dict[str, object]:
    return {
        "artifact_db_available": True,
        "timing": {
            "build_total_seconds": 1.234,
            "build_wall_seconds": 1.5,
            "build_phase_timings": {},
        },
        "languages": [],
        "totals": {
            "structure": {
                "files": 0,
                "nodes": 0,
                "edges": 0,
            },
            "callsites": {
                "observed_syntactic_callsites": 0,
                "filtered_pre_persist": 0,
                "persisted_callsites": 0,
                "persisted_accepted": 0,
                "persisted_dropped": 0,
            },
            "pre_persist_filter": {
                "no_in_repo_candidate": 0,
                "accepted_outside_in_repo": 0,
                "invalid_observation_shape": 0,
            },
            "call_materialization": {
                "callsite_pairs": 0,
                "finalized_call_edges": 0,
            },
        },
        "scopes": {},
    }


def test_cli_build_forwards_force_rebuild_flag(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    calls: list[bool] = []

    def _build(
        *,
        force_rebuild: bool = False,
        diagnostic: bool = False,
        diagnostic_verbose: bool = False,
    ):
        assert diagnostic is False
        assert diagnostic_verbose is False
        calls.append(force_rebuild)
        return _fake_committed_result()

    monkeypatch.setattr(repo_ops, "build", _build)
    monkeypatch.setattr(repo_ops, "snapshot_report", lambda snapshot_id: _fake_report())
    monkeypatch.setattr(repo_ops, "record_build_wall_time", lambda snapshot_id, wall_seconds: None)
    perf_values = iter([10.0, 11.25])
    monkeypatch.setattr(build_command, "perf_counter", lambda: next(perf_values))
    result = cli_runner.invoke(cli_app, ["build", "--force"])
    assert result.exit_code == 0
    assert calls == [True]
    assert "Wall time: 1.25s" in result.stdout
    assert "Core build time: 1.23s" in result.stdout


def test_cli_build_defaults_force_rebuild_false(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    calls: list[bool] = []

    def _build(
        *,
        force_rebuild: bool = False,
        diagnostic: bool = False,
        diagnostic_verbose: bool = False,
    ):
        assert diagnostic is False
        assert diagnostic_verbose is False
        calls.append(force_rebuild)
        return _fake_result()

    monkeypatch.setattr(repo_ops, "build", _build)
    monkeypatch.setattr(repo_ops, "snapshot_report", lambda snapshot_id: _fake_report())
    monkeypatch.setattr(repo_ops, "record_build_wall_time", lambda snapshot_id, wall_seconds: None)
    perf_values = iter([20.0, 20.5])
    monkeypatch.setattr(build_command, "perf_counter", lambda: next(perf_values))
    result = cli_runner.invoke(cli_app, ["build"])
    assert result.exit_code == 0
    assert calls == [False]


def test_cli_build_reports_reused_status_on_second_run(
    cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _snapshot_id = repo_with_snapshot
    runtime_config.io.write_config_text(
        repo_root,
        """languages:\n  python:\n    enabled: true\n\ndiscovery:\n  exclude_globs: []\n""",
    )
    commit_all(repo_root)
    monkeypatch.setattr(runtime_paths, "get_repo_root", lambda: repo_root)
    import sciona.cli.main as cli_module

    importlib.reload(cli_module)

    first = cli_runner.invoke(cli_module.app, ["build"])
    second = cli_runner.invoke(cli_module.app, ["build"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "Committed build inputs unchanged." in second.stdout
    assert "Summary:" not in second.stdout


def test_cli_build_warns_on_degraded_committed_result(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    monkeypatch.setattr(
        repo_ops,
        "build",
        lambda **kwargs: _fake_degraded_result(),
    )
    monkeypatch.setattr(repo_ops, "snapshot_report", lambda snapshot_id: _fake_report())
    monkeypatch.setattr(repo_ops, "record_build_wall_time", lambda snapshot_id, wall_seconds: None)
    perf_values = iter([30.0, 30.5])
    monkeypatch.setattr(build_command, "perf_counter", lambda: next(perf_values))

    result = cli_runner.invoke(cli_app, ["build"])

    assert result.exit_code == 0
    assert (
        "Warning: build completed with degraded analysis; partial results were committed."
        in result.stdout
    )


def test_cli_build_diagnostic_writes_repo_root_outputs(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _snapshot_id = repo_with_snapshot
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)
    monkeypatch.setattr(repo_ops, "build", lambda **kwargs: _fake_committed_result())
    monkeypatch.setattr(repo_ops, "snapshot_report", lambda snapshot_id: _fake_report())
    monkeypatch.setattr(repo_ops, "record_build_wall_time", lambda snapshot_id, wall_seconds: None)
    perf_values = iter([40.0, 40.25])
    monkeypatch.setattr(build_command, "perf_counter", lambda: next(perf_values))

    result = cli_runner.invoke(cli_app, ["build", "--diagnostic", "--verbose"])

    assert result.exit_code == 0
    build_status_path = repo_root / f"{repo_root.name}_build_status.json"
    verbose_path = repo_root / f"{repo_root.name}_pre_persist_verbose.json"
    assert build_status_path.exists()
    assert verbose_path.exists()
    build_status = json.loads(build_status_path.read_text(encoding="utf-8"))
    assert build_status["diagnostic_mode"] is True
    assert build_status["diagnostic_kind"] == "pre_persist_filter_best_effort"
    assert build_status["report"]["totals"]["pre_persist_filter"]["no_in_repo_candidate"] == 0
