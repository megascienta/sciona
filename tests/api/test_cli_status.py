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


def _fake_summary():
    return {
        "snapshot_id": "snap-1",
        "created_at": "2026-03-04T00:00:00Z",
        "build_total_seconds": 1.234,
        "build_wall_seconds": 1.5,
        "build_phase_timings": {
            "build_structural_index": 0.8,
            "rebuild_graph_rollups": 0.1,
        },
        "artifact_db_available": True,
        "languages": [
            {
                "language": "python",
                "files": 10,
                "nodes": 20,
                "edges": 30,
                "call_sites": {
                    "eligible": 10,
                    "accepted": 9,
                    "dropped": 1,
                    "success_rate": 0.9,
                },
                "call_site_funnel": {
                    "observed_syntactic_callsites": 12,
                    "filtered_pre_persist": 2,
                    "persisted_callsites": 10,
                    "persisted_accepted": 9,
                    "persisted_dropped": 1,
                    "record_drops": {"no_resolved_callees": 1},
                    "conservation_ok": True,
                },
                "call_sites_by_scope": {
                    "non_tests": {
                        "eligible": 8,
                        "accepted": 8,
                        "dropped": 0,
                        "success_rate": 1.0,
                    },
                    "tests": {
                        "eligible": 2,
                        "accepted": 1,
                        "dropped": 1,
                        "success_rate": 0.5,
                    },
                },
                "drop_reasons": {"no_candidates": 1},
                "filtered_pre_persist_buckets": {"zero_candidate_count": 2},
                "drop_classification": {"external_likely": 1},
            }
        ],
        "totals": {
            "files": 10,
            "nodes": 20,
            "edges": 30,
            "call_sites": {
                "eligible": 10,
                "accepted": 9,
                "dropped": 1,
                "success_rate": 0.9,
            },
            "call_site_funnel": {
                "observed_syntactic_callsites": 12,
                "filtered_pre_persist": 2,
                "persisted_callsites": 10,
                "persisted_accepted": 9,
                "persisted_dropped": 1,
                "record_drops": {"no_resolved_callees": 1},
                "conservation_ok": True,
            },
            "call_sites_by_scope": {
                "non_tests": {
                    "eligible": 8,
                    "accepted": 8,
                    "dropped": 0,
                    "success_rate": 1.0,
                },
                "tests": {
                    "eligible": 2,
                    "accepted": 1,
                    "dropped": 1,
                    "success_rate": 0.5,
                },
            },
            "filtered_pre_persist_buckets": {"zero_candidate_count": 2},
            "drop_classification": {"external_likely": 1},
        },
    }


def test_cli_status_default_uses_short_summary(cli_app, cli_runner, monkeypatch):
    calls: list[bool] = []

    def _summary(snapshot_id: str, include_failure_reasons: bool = False):
        assert snapshot_id == "snap-1"
        calls.append(include_failure_reasons)
        return _fake_summary()

    monkeypatch.setattr(repo_ops, "status", _fake_status)
    monkeypatch.setattr(repo_ops, "snapshot_report", _summary)

    result = cli_runner.invoke(cli_app, ["status"])

    assert result.exit_code == 0
    assert calls == [False]
    assert "Last build:" in result.stdout
    assert "Wall time: 1.50s" in result.stdout
    assert "Core build time: 1.23s" in result.stdout
    assert "Summary:" in result.stdout
    assert "Discovery:" not in result.stdout
    assert "call_materialization:" not in result.stdout
    assert "failed reasons:" not in result.stdout
    assert "Last build:\n  Snapshot:" not in result.stdout
    assert "Last build:\n  Created:" not in result.stdout


def test_cli_status_full_emits_failure_reasons(cli_app, cli_runner, monkeypatch):
    calls: list[bool] = []

    def _summary(snapshot_id: str, include_failure_reasons: bool = False):
        assert snapshot_id == "snap-1"
        calls.append(include_failure_reasons)
        return _fake_summary()

    monkeypatch.setattr(repo_ops, "status", _fake_status)
    monkeypatch.setattr(repo_ops, "snapshot_report", _summary)

    result = cli_runner.invoke(cli_app, ["status", "--full"])

    assert result.exit_code == 0
    assert calls == [True]
    assert "call_materialization:" in result.stdout
    assert "call_funnel: observed=12, filtered_pre_persist=2, persisted=10, accepted=9, dropped=1" in result.stdout
    assert "Wall time: 1.50s" in result.stdout
    assert "Core build time: 1.23s" in result.stdout
    assert "non_tests:" in result.stdout
    assert "tests:" in result.stdout
    assert "filtered_pre_persist: zero_candidate_count=2" in result.stdout
    assert "failed reasons: no_candidates=1" in result.stdout
    assert "drop classification: external_likely=1" in result.stdout


def test_cli_status_json_emits_payload(cli_app, cli_runner, monkeypatch):
    calls: list[bool] = []

    def _summary(snapshot_id: str, include_failure_reasons: bool = False):
        assert snapshot_id == "snap-1"
        calls.append(include_failure_reasons)
        return _fake_summary()

    monkeypatch.setattr(repo_ops, "status", _fake_status)
    monkeypatch.setattr(repo_ops, "snapshot_report", _summary)

    result = cli_runner.invoke(cli_app, ["status", "--json"])

    assert result.exit_code == 0
    assert calls == [True]
    payload = json.loads(result.stdout)
    assert payload["repo_root"] == os.path.relpath("/tmp/repo", start=os.getcwd())
    assert not payload["repo_root"].startswith("/")
    assert payload["latest_snapshot"] == "snap-1"
    assert payload["status_report_version"] == 1
    assert payload["summary"]["snapshot_id"] == "snap-1"
    assert payload["summary"]["build_total_seconds"] == 1.234
    assert payload["summary"]["build_wall_seconds"] == 1.5
    assert payload["summary"]["build_phase_timings"]["build_structural_index"] == 0.8
    assert payload["summary"]["languages"][0]["drop_reasons"]["no_candidates"] == 1


def test_cli_status_output_writes_json_file(cli_app, cli_runner, monkeypatch, tmp_path):
    calls: list[bool] = []

    def _summary(snapshot_id: str, include_failure_reasons: bool = False):
        assert snapshot_id == "snap-1"
        calls.append(include_failure_reasons)
        return _fake_summary()

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
    assert payload["summary"]["build_total_seconds"] == 1.234
    assert payload["summary"]["build_wall_seconds"] == 1.5
    assert payload["summary"]["build_phase_timings"]["rebuild_graph_rollups"] == 0.1
    assert payload["summary"]["languages"][0]["drop_reasons"]["no_candidates"] == 1


def test_cli_status_json_ignores_full_flag_for_payload_shape(
    cli_app, cli_runner, monkeypatch
):
    def _summary(snapshot_id: str, include_failure_reasons: bool = False):
        assert snapshot_id == "snap-1"
        assert include_failure_reasons is True
        return _fake_summary()

    monkeypatch.setattr(repo_ops, "status", _fake_status)
    monkeypatch.setattr(repo_ops, "snapshot_report", _summary)

    plain = cli_runner.invoke(cli_app, ["status", "--json"])
    flagged = cli_runner.invoke(cli_app, ["status", "--json", "--full"])

    assert plain.exit_code == 0
    assert flagged.exit_code == 0
    assert json.loads(plain.stdout) == json.loads(flagged.stdout)


def test_cli_status_full_emits_low_node_warning(cli_app, cli_runner, monkeypatch):
    def _summary(snapshot_id: str, include_failure_reasons: bool = False):
        assert snapshot_id == "snap-1"
        payload = _fake_summary()
        payload["languages"][0]["structural_density"] = {
            "inflation_warning": True,
            "low_node_file_ratio": 0.72,
        }
        payload["totals"]["structural_density"] = {
            "inflation_warning": True,
            "low_node_file_ratio": 0.68,
        }
        return payload

    monkeypatch.setattr(repo_ops, "status", _fake_status)
    monkeypatch.setattr(repo_ops, "snapshot_report", _summary)

    result = cli_runner.invoke(cli_app, ["status", "--full"])

    assert result.exit_code == 0
    assert "warning: low-node file ratio is high (72.0%)" in result.stdout
    assert "warning: low-node file ratio is high (68.0%)" in result.stdout
