# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
import os
from types import SimpleNamespace

from sciona.cli import repo_ops


def _fake_status():
    return SimpleNamespace(
        repo_root="/tmp/repo",
        tool_version="1.0.0",
        schema_version="1.0.0",
        snapshot_count=1,
        latest_snapshot="snap-1",
        latest_created="2026-03-04T00:00:00Z",
        db_exists=True,
    )


def _fake_report():
    return {
        "artifact_db_available": True,
        "labels": {
            "sections": {
                "structure": "Structure",
                "callsites": "Callsites",
                "call_materialization": "Call Materialization",
                "timing": "Timing",
            },
            "fields": {
                "files": "Files",
                "nodes": "Nodes",
                "edges": "Edges",
                "observed_syntactic_callsites": "Observed Syntactic Callsites",
                "accepted_callsites": "Accepted Callsites",
                "not_accepted_callsites": "Not Accepted Callsites",
                "finalized_call_edges": "Finalized Call Edges",
                "build_total_seconds": "Build Total Seconds",
                "build_wall_seconds": "Build Wall Seconds",
            },
            "scopes": {
                "non_tests": "Non-Tests",
                "tests": "Tests",
            },
            "phases": {
                "build_structural_index": "Build Structural Index",
                "prepare_callsite_pairs": "Prepare Callsite Pairs",
                "write_callsite_pairs": "Write Callsite Pairs",
                "rebuild_graph_rollups": "Rebuild Graph Rollups",
            },
        },
        "timing": {
            "build_total_seconds": 1.234,
            "build_wall_seconds": 1.5,
            "build_phase_timings": {
                "build_structural_index": 0.8,
                "prepare_callsite_pairs": 0.3,
                "write_callsite_pairs": 0.05,
                "rebuild_graph_rollups": 0.1,
            },
        },
        "languages": {
            "python": {
                "structure": {
                    "files": 10,
                    "nodes": 20,
                    "edges": 19,
                },
                "callsites": {
                    "observed_syntactic_callsites": 12,
                    "accepted_callsites": 9,
                    "not_accepted_callsites": 3,
                },
                "call_materialization": {
                    "finalized_call_edges": 9,
                },
            }
        },
        "totals": {
            "structure": {
                "files": 10,
                "nodes": 20,
                "edges": 19,
            },
            "callsites": {
                "observed_syntactic_callsites": 12,
                "accepted_callsites": 9,
                "not_accepted_callsites": 3,
            },
            "call_materialization": {
                "finalized_call_edges": 9,
            },
        },
        "scopes": {
            "non_tests": {
                "structure": {
                    "files": 8,
                    "nodes": 16,
                    "edges": 17,
                },
                "callsites": {
                    "observed_syntactic_callsites": 10,
                    "accepted_callsites": 7,
                    "not_accepted_callsites": 3,
                },
                "call_materialization": {
                    "finalized_call_edges": 8,
                },
            },
            "tests": {
                "structure": {
                    "files": 2,
                    "nodes": 4,
                    "edges": 2,
                },
                "callsites": {
                    "observed_syntactic_callsites": 2,
                    "accepted_callsites": 2,
                    "not_accepted_callsites": 0,
                },
                "call_materialization": {
                    "finalized_call_edges": 1,
                },
            },
        },
    }


def test_cli_status_default_uses_short_summary(cli_app, cli_runner, monkeypatch):
    calls: list[bool] = []

    def _summary(snapshot_id: str, include_failure_reasons: bool = False):
        assert snapshot_id == "snap-1"
        calls.append(include_failure_reasons)
        return _fake_report()

    monkeypatch.setattr(repo_ops, "status", _fake_status)
    monkeypatch.setattr(repo_ops, "snapshot_report", _summary)

    result = cli_runner.invoke(cli_app, ["status"])

    assert result.exit_code == 0
    assert calls == [False]
    assert "Last build:" in result.stdout
    assert "Wall time: 1.50s" in result.stdout
    assert "Core build time: 1.23s" in result.stdout
    assert "Summary:" in result.stdout
    assert "python: 10 files, 20 nodes, 19 edges" in result.stdout
    assert "call_materialization:" not in result.stdout
    assert "not_accepted_callsites:" not in result.stdout


def test_cli_status_verbose_emits_grouped_direct_metrics(cli_app, cli_runner, monkeypatch):
    calls: list[bool] = []

    def _summary(snapshot_id: str, include_failure_reasons: bool = False):
        assert snapshot_id == "snap-1"
        calls.append(include_failure_reasons)
        return _fake_report()

    monkeypatch.setattr(repo_ops, "status", _fake_status)
    monkeypatch.setattr(repo_ops, "snapshot_report", _summary)

    result = cli_runner.invoke(cli_app, ["status", "--verbose"])

    assert result.exit_code == 0
    assert calls == [True]
    assert (
        "callsites: observed=12, accepted=9, not_accepted=3"
        in result.stdout
    )
    assert (
        "call_materialization: finalized_call_edges=9"
        in result.stdout
    )
    assert "not_accepted_callsites:" not in result.stdout
    assert "non_tests:" in result.stdout
    assert "structure: 8 files, 16 nodes, 17 edges" in result.stdout
    assert (
        "callsites: observed=10, accepted=7, not_accepted=3"
        in result.stdout
    )
    assert "finalized_call_edges=8" in result.stdout
    assert "pair_expansion:" not in result.stdout
    assert "conservation mismatch" not in result.stdout


def test_cli_status_output_writes_json_file(cli_app, cli_runner, monkeypatch, tmp_path):
    calls: list[bool] = []

    def _summary(snapshot_id: str, include_failure_reasons: bool = False):
        assert snapshot_id == "snap-1"
        calls.append(include_failure_reasons)
        return _fake_report()

    monkeypatch.setattr(repo_ops, "status", _fake_status)
    monkeypatch.setattr(repo_ops, "snapshot_report", _summary)

    output_path = tmp_path / "reports" / "status.json"
    result = cli_runner.invoke(cli_app, ["status", "--output", str(output_path)])

    assert result.exit_code == 0
    assert calls == [True]
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status_report_version"] == 1
    assert not payload["repo_root"].startswith("/")
    assert payload["detailed"] is True
    assert payload["artifact_db_available"] is True
    assert payload["report"]["timing"]["build_total_seconds"] == 1.234
    assert payload["report"]["timing"]["build_wall_seconds"] == 1.5
    assert payload["report"]["timing"]["build_phase_timings"]["prepare_callsite_pairs"] == 0.3
    assert payload["report"]["timing"]["build_phase_timings"]["write_callsite_pairs"] == 0.05
    assert payload["report"]["timing"]["build_phase_timings"]["rebuild_graph_rollups"] == 0.1
    assert payload["report"]["totals"]["call_materialization"]["finalized_call_edges"] == 9
