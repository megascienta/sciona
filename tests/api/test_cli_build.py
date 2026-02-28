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


def test_cli_build_forwards_force_rebuild_flag(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    calls: list[bool] = []

    def _build(*, force_rebuild: bool = False):
        calls.append(force_rebuild)
        return _fake_result()

    monkeypatch.setattr(api_cli, "build", _build)
    result = cli_runner.invoke(cli_app, ["build", "--force-rebuild"])
    assert result.exit_code == 0
    assert calls == [True]


def test_cli_build_defaults_force_rebuild_false(
    cli_app, cli_runner, repo_with_snapshot, monkeypatch
):
    calls: list[bool] = []

    def _build(*, force_rebuild: bool = False):
        calls.append(force_rebuild)
        return _fake_result()

    monkeypatch.setattr(api_cli, "build", _build)
    result = cli_runner.invoke(cli_app, ["build"])
    assert result.exit_code == 0
    assert calls == [False]
