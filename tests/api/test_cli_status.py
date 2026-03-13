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
            "prepare_callsite_pairs": 0.3,
            "write_callsite_pairs": 0.05,
            "rebuild_graph_rollups": 0.1,
        },
        "artifact_db_available": True,
        "languages": [
            {
                "language": "python",
                "files": 10,
                "nodes": 20,
                "edges": 30,
                "callsite_pairs": {"count": 11},
                "finalized_call_edges": {"count": 9},
                "call_site_funnel": {
                    "observed_syntactic_callsites": 12,
                    "filtered_pre_persist": 2,
                    "persisted_callsites": 10,
                    "persisted_accepted": 9,
                    "persisted_dropped": 1,
                    "record_drops": {"no_resolved_callees": 1},
                    "conservation_ok": True,
                },
                "persisted_callsite_pair_expansion": {
                    "persisted_callsites": 10,
                    "persisted_callsites_with_zero_pairs": 1,
                    "persisted_callsites_with_one_pair": 7,
                    "persisted_callsites_with_multiple_pairs": 2,
                    "pair_expansion_factor": 1.1,
                    "multi_pair_share": 0.2,
                    "max_pairs_for_single_persisted_callsite": 3,
                },
                "callsite_pairs_by_scope": {
                    "non_tests": {"count": 8},
                    "tests": {"count": 3},
                },
                "finalized_call_edges_by_scope": {
                    "non_tests": {"count": 8},
                    "tests": {"count": 1},
                },
                "persisted_callsite_pair_expansion_by_scope": {
                    "non_tests": {
                        "persisted_callsites": 8,
                        "persisted_callsites_with_zero_pairs": 1,
                        "persisted_callsites_with_one_pair": 5,
                        "persisted_callsites_with_multiple_pairs": 2,
                        "pair_expansion_factor": 1.0,
                        "multi_pair_share": 0.25,
                        "max_pairs_for_single_persisted_callsite": 3,
                    },
                    "tests": {
                        "persisted_callsites": 2,
                        "persisted_callsites_with_zero_pairs": 0,
                        "persisted_callsites_with_one_pair": 2,
                        "persisted_callsites_with_multiple_pairs": 0,
                        "pair_expansion_factor": 1.5,
                        "multi_pair_share": 0.0,
                        "max_pairs_for_single_persisted_callsite": 1,
                    },
                },
                "filtered_pre_persist_buckets": {
                    "no_in_repo_candidate_terminal": 2,
                    "no_in_repo_candidate_qualified": 0,
                    "accepted_outside_in_repo": 0,
                    "invalid_observation_shape": 0,
                },
                "filtered_pre_persist_buckets_by_scope": {
                    "non_tests": {
                        "no_in_repo_candidate_terminal": 2,
                        "no_in_repo_candidate_qualified": 0,
                        "accepted_outside_in_repo": 0,
                        "invalid_observation_shape": 0,
                    },
                    "tests": {
                        "no_in_repo_candidate_terminal": 0,
                        "no_in_repo_candidate_qualified": 0,
                        "accepted_outside_in_repo": 0,
                        "invalid_observation_shape": 0,
                    },
                },
            }
        ],
        "totals": {
            "files": 10,
            "nodes": 20,
            "edges": 30,
            "callsite_pairs": {"count": 11},
            "finalized_call_edges": {"count": 9},
            "call_site_funnel": {
                "observed_syntactic_callsites": 12,
                "filtered_pre_persist": 2,
                "persisted_callsites": 10,
                "persisted_accepted": 9,
                "persisted_dropped": 1,
                "record_drops": {"no_resolved_callees": 1},
                "conservation_ok": True,
            },
            "persisted_callsite_pair_expansion": {
                "persisted_callsites": 10,
                "persisted_callsites_with_zero_pairs": 1,
                "persisted_callsites_with_one_pair": 7,
                "persisted_callsites_with_multiple_pairs": 2,
                "pair_expansion_factor": 1.1,
                "multi_pair_share": 0.2,
                "max_pairs_for_single_persisted_callsite": 3,
            },
            "callsite_pairs_by_scope": {
                "non_tests": {"count": 8},
                "tests": {"count": 3},
            },
            "finalized_call_edges_by_scope": {
                "non_tests": {"count": 8},
                "tests": {"count": 1},
            },
            "persisted_callsite_pair_expansion_by_scope": {
                "non_tests": {
                    "persisted_callsites": 8,
                    "persisted_callsites_with_zero_pairs": 1,
                    "persisted_callsites_with_one_pair": 5,
                    "persisted_callsites_with_multiple_pairs": 2,
                    "pair_expansion_factor": 1.0,
                    "multi_pair_share": 0.25,
                    "max_pairs_for_single_persisted_callsite": 3,
                },
                "tests": {
                    "persisted_callsites": 2,
                    "persisted_callsites_with_zero_pairs": 0,
                    "persisted_callsites_with_one_pair": 2,
                    "persisted_callsites_with_multiple_pairs": 0,
                    "pair_expansion_factor": 1.5,
                    "multi_pair_share": 0.0,
                    "max_pairs_for_single_persisted_callsite": 1,
                },
            },
            "filtered_pre_persist_buckets": {
                "no_in_repo_candidate_terminal": 2,
                "no_in_repo_candidate_qualified": 0,
                "accepted_outside_in_repo": 0,
                "invalid_observation_shape": 0,
            },
            "filtered_pre_persist_buckets_by_scope": {
                "non_tests": {
                    "no_in_repo_candidate_terminal": 2,
                    "no_in_repo_candidate_qualified": 0,
                    "accepted_outside_in_repo": 0,
                    "invalid_observation_shape": 0,
                },
                "tests": {
                    "no_in_repo_candidate_terminal": 0,
                    "no_in_repo_candidate_qualified": 0,
                    "accepted_outside_in_repo": 0,
                    "invalid_observation_shape": 0,
                },
            },
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
    assert "callsite_pairs:" not in result.stdout
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
    assert "callsite_pairs:" in result.stdout
    assert "finalized_call_edges:" in result.stdout
    assert "call_funnel: observed=12, filtered_pre_persist=2, persisted=10, accepted=9, dropped=1" in result.stdout
    assert "Wall time: 1.50s" in result.stdout
    assert "Core build time: 1.23s" in result.stdout
    assert "non_tests: pairs=8, edges=8" in result.stdout
    assert "tests: pairs=3, edges=1" in result.stdout
    assert "pair_expansion: persisted=10, zero=1, one=7, multiple=2, factor=1.1000x, multi_pair_share=20.0%, max=3" in result.stdout
    assert "non_tests: persisted=8, zero=1, one=5, multiple=2, factor=1.0000x, multi_pair_share=25.0%, max=3" in result.stdout
    assert (
        "filtered_pre_persist: no_in_repo_candidate_terminal=2, "
        "no_in_repo_candidate_qualified=0, accepted_outside_in_repo=0, "
        "invalid_observation_shape=0"
    ) in result.stdout


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
    assert payload["summary"]["build_phase_timings"]["prepare_callsite_pairs"] == 0.3
    assert payload["summary"]["build_phase_timings"]["write_callsite_pairs"] == 0.05
    assert payload["summary"]["languages"][0]["callsite_pairs"]["count"] == 11


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
    assert payload["summary"]["build_phase_timings"]["prepare_callsite_pairs"] == 0.3
    assert payload["summary"]["build_phase_timings"]["write_callsite_pairs"] == 0.05
    assert payload["summary"]["build_phase_timings"]["rebuild_graph_rollups"] == 0.1
    assert payload["summary"]["languages"][0]["callsite_pairs"]["count"] == 11


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
