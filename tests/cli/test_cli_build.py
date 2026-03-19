# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import importlib
import json

from sciona.cli import repo_ops
from sciona.cli.commands import register_build as build_command
from sciona.pipelines.ops import repo as repo_pipeline
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
        "languages": {},
        "totals": {
            "structure": {
                "files": 0,
                "nodes": 0,
                "edges": 0,
            },
            "callsites": {
                "observed_syntactic_callsites": 0,
                "accepted_callsites": 0,
                "not_accepted_callsites": 0,
            },
            "not_accepted_calls": {
                "out_of_scope_call": 0,
                "weak_static_evidence": 0,
                "structural_gap": 0,
                "unclassified": 0,
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


def test_cli_build_records_wall_time_before_snapshot_report(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    recorded: list[float] = []

    monkeypatch.setattr(repo_ops, "build", lambda **kwargs: _fake_committed_result())

    def _record_build_wall_time(snapshot_id: str, wall_seconds: float) -> None:
        assert snapshot_id == "snap"
        recorded.append(wall_seconds)

    def _snapshot_report(snapshot_id: str) -> dict[str, object]:
        assert snapshot_id == "snap"
        assert recorded == [1.25]
        return _fake_report()

    monkeypatch.setattr(repo_ops, "record_build_wall_time", _record_build_wall_time)
    monkeypatch.setattr(repo_ops, "snapshot_report", _snapshot_report)
    perf_values = iter([10.0, 11.25])
    monkeypatch.setattr(build_command, "perf_counter", lambda: next(perf_values))

    result = cli_runner.invoke(cli_app, ["build"])

    assert result.exit_code == 0
    assert recorded == [1.25]


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
    result = _fake_committed_result()
    result = BuildResult(
        **{
            **result.__dict__,
            "diagnostic_report": {
                "totals": {},
                "by_language": {},
                "by_scope": {"non_tests": {}, "tests": {}},
                "observations": [],
            },
        }
    )
    monkeypatch.setattr(repo_ops, "build", lambda **kwargs: result)
    monkeypatch.setattr(repo_ops, "snapshot_report", lambda snapshot_id: _fake_report())
    monkeypatch.setattr(
        repo_pipeline,
        "persisted_drop_diagnostics",
        lambda snapshot_id, repo_root=None: {},
    )
    monkeypatch.setattr(repo_ops, "record_build_wall_time", lambda snapshot_id, wall_seconds: None)
    perf_values = iter([40.0, 40.25])
    monkeypatch.setattr(build_command, "perf_counter", lambda: next(perf_values))

    result = cli_runner.invoke(cli_app, ["build", "--diagnostic", "--verbose"])

    assert result.exit_code == 0
    build_status_path = repo_root / f"{repo_root.name}_build_status.json"
    verbose_path = repo_root / f"{repo_root.name}_not_accepted_verbose.json"
    assert build_status_path.exists()
    assert verbose_path.exists()
    build_status = json.loads(build_status_path.read_text(encoding="utf-8"))
    assert build_status["diagnostic_mode"] is True
    assert build_status["diagnostic_kind"] == "rejected_calls_best_effort"
    assert "no_in_repo_candidate" not in build_status["report"]["totals"]["not_accepted_calls"]
    verbose_payload = json.loads(verbose_path.read_text(encoding="utf-8"))
    assert verbose_payload["diagnostic_mode"] is True
    assert verbose_payload["diagnostic_kind"] == "rejected_calls_best_effort"
    assert "buckets" in verbose_payload


def test_cli_build_diagnostic_enriches_not_accepted_calls(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _snapshot_id = repo_with_snapshot
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)
    result = _fake_committed_result()
    result = BuildResult(
        **{
            **result.__dict__,
            "diagnostic_report": {
                "totals": {
                    "likely_external_dependency": 2,
                    "likely_standard_library_or_builtin": 1,
                },
                "by_language": {
                    "python": {
                        "likely_external_dependency": 2,
                        "likely_standard_library_or_builtin": 1,
                    }
                },
                "by_scope": {
                    "non_tests": {
                        "likely_external_dependency": 2,
                        "likely_standard_library_or_builtin": 1,
                    },
                    "tests": {},
                },
                "observations": [],
            },
        }
    )
    monkeypatch.setattr(repo_ops, "build", lambda **kwargs: result)
    monkeypatch.setattr(repo_ops, "snapshot_report", lambda snapshot_id: _fake_report())
    monkeypatch.setattr(
        repo_pipeline,
        "persisted_drop_diagnostics",
        lambda snapshot_id, repo_root=None: {},
    )
    monkeypatch.setattr(repo_ops, "record_build_wall_time", lambda snapshot_id, wall_seconds: None)
    perf_values = iter([50.0, 50.25])
    monkeypatch.setattr(build_command, "perf_counter", lambda: next(perf_values))

    result_cli = cli_runner.invoke(cli_app, ["build", "--diagnostic"])

    assert result_cli.exit_code == 0
    build_status_path = repo_root / f"{repo_root.name}_build_status.json"
    build_status = json.loads(build_status_path.read_text(encoding="utf-8"))
    assert build_status["report"]["totals"]["not_accepted_calls"] == {
        "out_of_scope_call": 3,
        "weak_static_evidence": 0,
        "structural_gap": 0,
        "unclassified": 0,
    }


def test_cli_build_verbose_sidecar_groups_callsites_by_bucket(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    repo_root, _snapshot_id = repo_with_snapshot
    monkeypatch.setattr(repo_ops, "get_repo_root", lambda: repo_root)
    result = _fake_committed_result()
    result = BuildResult(
        **{
            **result.__dict__,
            "diagnostic_report": {
                "totals": {},
                "by_language": {},
                "by_scope": {},
                "observations": [
                    {
                        "bucket": "likely_unindexed_symbol",
                        "identifier": "helper",
                        "file_path": "pkg/a.py",
                        "reasons": [],
                        "signals": [],
                    },
                    {
                        "bucket": "likely_unindexed_symbol",
                        "identifier": "worker",
                        "file_path": "pkg/b.py",
                        "reasons": [],
                        "signals": [],
                    },
                ],
            },
        }
    )
    monkeypatch.setattr(repo_ops, "build", lambda **kwargs: result)
    monkeypatch.setattr(repo_ops, "snapshot_report", lambda snapshot_id: _fake_report())
    monkeypatch.setattr(
        repo_pipeline,
        "persisted_drop_diagnostics",
        lambda snapshot_id, repo_root=None: {
            "persisted_drop_observations": [
                {
                    "caller_structural_id": "caller",
                    "caller_qualified_name": "pkg.alpha.run",
                    "caller_module": "pkg.alpha",
                    "file_path": "pkg/a.py",
                    "language": "python",
                    "identifier": "socket.in(room).emit",
                    "ordinal": 1,
                    "drop_reason": "ambiguous_multiple_in_scope_candidates",
                    "candidate_count": 2,
                    "callee_kind": "qualified",
                    "in_scope_candidate_count": 2,
                    "candidate_module_hints": "pkg.alpha,pkg.beta",
                }
            ]
        },
    )
    monkeypatch.setattr(repo_ops, "record_build_wall_time", lambda snapshot_id, wall_seconds: None)
    perf_values = iter([60.0, 60.25])
    monkeypatch.setattr(build_command, "perf_counter", lambda: next(perf_values))

    result_cli = cli_runner.invoke(cli_app, ["build", "--diagnostic", "--verbose"])

    assert result_cli.exit_code == 0
    verbose_path = repo_root / f"{repo_root.name}_not_accepted_verbose.json"
    verbose_payload = json.loads(verbose_path.read_text(encoding="utf-8"))
    assert verbose_payload["buckets"]["weak_static_evidence"]["count"] == 2
    assert verbose_payload["buckets"]["weak_static_evidence"]["phases"] == {
        "pre_persist": 2
    }
    assert verbose_payload["buckets"]["out_of_scope_call"]["count"] == 1
    assert verbose_payload["buckets"]["out_of_scope_call"]["phases"] == {
        "post_persist": 1
    }
    assert verbose_payload["phase_counts"] == {"post_persist": 1, "pre_persist": 2}
    assert verbose_payload["problematic_files"][0]["file_path"] == "pkg/a.py"
    assert verbose_payload["problematic_files"][0]["phases"] == {
        "post_persist": 1,
        "pre_persist": 1,
    }
