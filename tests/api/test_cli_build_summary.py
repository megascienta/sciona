# SPDX-License-Identifier: MIT

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


def _fake_summary():
    return {
        "snapshot_id": "snap",
        "created_at": "2026-03-04T00:00:00Z",
        "artifact_db_available": True,
        "languages": [
            {
                "language": "python",
                "files": 1,
                "nodes": 1,
                "edges": 0,
                "call_sites": {
                    "eligible": 0,
                    "accepted": 0,
                    "dropped": 0,
                    "success_rate": None,
                },
            }
        ],
        "totals": {
            "files": 1,
            "nodes": 1,
            "edges": 0,
            "call_sites": {
                "eligible": 0,
                "accepted": 0,
                "dropped": 0,
                "success_rate": None,
            },
        },
    }


def test_cli_build_emits_summary_block(cli_app, cli_runner, monkeypatch):
    monkeypatch.setattr(api_cli, "build", lambda force_rebuild=False: _fake_result())
    monkeypatch.setattr(api_cli, "snapshot_report", lambda snapshot_id: _fake_summary())

    result = cli_runner.invoke(cli_app, ["build"])

    assert result.exit_code == 0
    assert "Summary:" in result.stdout
    assert "Discovery summary:" not in result.stdout
    assert "Source candidates by extension:" not in result.stdout
