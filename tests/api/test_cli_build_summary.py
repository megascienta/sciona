# SPDX-License-Identifier: MIT

from __future__ import annotations

from sciona.cli import repo_ops
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
        imports_seen=3,
        imports_internal=2,
        imports_filtered_not_internal=1,
        imports_by_language={
            "python": {
                "imports_seen": 3,
                "imports_internal": 2,
                "imports_filtered_not_internal": 1,
            }
        },
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
                "callsite_pairs": {"count": 0},
                "finalized_call_edges": {"count": 0},
            }
        ],
        "totals": {
            "files": 1,
            "nodes": 1,
            "edges": 0,
            "callsite_pairs": {"count": 0},
            "finalized_call_edges": {"count": 0},
        },
    }


def test_cli_build_emits_summary_block(cli_app, cli_runner, monkeypatch):
    monkeypatch.setattr(repo_ops, "build", lambda force_rebuild=False: _fake_result())
    monkeypatch.setattr(repo_ops, "snapshot_report", lambda snapshot_id: _fake_summary())

    result = cli_runner.invoke(cli_app, ["build"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "Committed build inputs unchanged."
    assert "call_materialization:" not in result.stdout
    assert "imports_seen:" not in result.stdout
    assert "Diagnostics:" not in result.stdout
    assert "Discovery summary:" not in result.stdout
    assert "Source candidates by extension:" not in result.stdout
