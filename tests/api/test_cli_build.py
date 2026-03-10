# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from sciona.api import cli as api_cli
from sciona.pipelines.exec.build import BuildResult


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


def _fake_summary() -> dict[str, object]:
    return {
        "snapshot_id": "snap",
        "created_at": "2026-03-10T00:00:00Z",
        "build_total_seconds": 1.234,
        "artifact_db_available": True,
        "languages": [],
        "totals": {"files": 0, "nodes": 0, "edges": 0, "call_sites": {}},
    }


def test_cli_build_forwards_force_rebuild_flag(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    calls: list[bool] = []

    def _build(*, force_rebuild: bool = False):
        calls.append(force_rebuild)
        return _fake_result()

    monkeypatch.setattr(api_cli, "build", _build)
    monkeypatch.setattr(api_cli, "snapshot_report", lambda snapshot_id: _fake_summary())
    result = cli_runner.invoke(cli_app, ["build", "--force"])
    assert result.exit_code == 0
    assert calls == [True]
    assert "Total build time: 1.23s" in result.stdout


def test_cli_build_defaults_force_rebuild_false(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    calls: list[bool] = []

    def _build(*, force_rebuild: bool = False):
        calls.append(force_rebuild)
        return _fake_result()

    monkeypatch.setattr(api_cli, "build", _build)
    monkeypatch.setattr(api_cli, "snapshot_report", lambda snapshot_id: _fake_summary())
    result = cli_runner.invoke(cli_app, ["build"])
    assert result.exit_code == 0
    assert calls == [False]
