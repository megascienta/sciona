# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from experiments.reducers.validation.orchestrator import (
    _bootstrap_micro_ci,
    _select_threshold_profile,
)
from experiments.reducers.validation.report import render_summary, write_json


def test_select_threshold_profile_multi_language() -> None:
    profile, thresholds = _select_threshold_profile(
        [
            {"language": "python"},
            {"language": "java"},
        ]
    )
    assert profile == "multi_language"
    assert thresholds["contract_recall_min"] <= 0.95


def test_bootstrap_micro_ci_shape() -> None:
    rows = [
        {"metrics_reducer_vs_contract": {"tp": 10, "fp": 2, "fn": 1}},
        {"metrics_reducer_vs_contract": {"tp": 7, "fp": 1, "fn": 2}},
        {"metrics_reducer_vs_contract": {"tp": 3, "fp": 1, "fn": 4}},
    ]
    ci = _bootstrap_micro_ci(rows, "metrics_reducer_vs_contract", seed=7, rounds=50)
    assert ci["n"] == 3
    assert ci["precision_ci95"] is not None
    assert ci["recall_ci95"] is not None


def test_render_summary_includes_action_and_reason_sections() -> None:
    payload = {
        "summary": ["repo=test", "sampled_nodes=1", "invariants_passed=True"],
        "core_metrics": {"static_contract_recall": 1.0, "static_overreach_rate": 0.0},
        "invariants": {"passed": True, "hard_passed": True},
        "quality_gates": {"threshold_profile": "single_language"},
        "internal_integrity": {"valid": True, "projection": {}, "determinism": {}},
        "static_contract_alignment": {},
        "enriched_truth_alignment": {
            "reason_breakdown": {"reducer": {"dynamic": {"tp": 1, "fn": 1, "recall": 0.5}}},
            "scope_split_counts": {"excluded_out_of_scope_edges": 1},
        },
        "enrichment_practical": {},
        "micro_metrics_by_language": {},
        "micro_metrics_by_language_and_kind": {},
        "per_node": [],
        "population_by_language": {},
        "independent_totals": {},
        "out_of_contract_breakdown": {},
        "call_form_recall": {},
        "mismatch_attribution_breakdown": {},
        "metric_definitions": {},
        "report_schema_version": "test",
        "action_priority_board": [{"priority": "high", "area": "core", "issue": "x", "evidence": {}}],
    }
    lines = render_summary(payload)
    text = "\n".join(lines)
    assert "Reason-level expanded proxy recall:" in text
    assert "## Action Priority Board" in text


def test_write_json_validates_minimum_payload_shape(tmp_path) -> None:
    payload = {
        "summary": ["repo=test", "sampled_nodes=1"],
        "invariants": {"passed": True},
        "quality_gates": {"threshold_profile": "single_language"},
        "per_node": [
            {
                "entity": "fixture.sample.entry",
                "language": "python",
                "kind": "function",
                "file_path": "sample.py",
                "module_qualified_name": "fixture.sample",
                "metrics_reducer_vs_db": {"tp": 1, "fp": 0, "fn": 0},
            }
        ],
    }
    out = tmp_path / "report.json"
    write_json(out, payload)
    assert out.exists()


def test_write_json_rejects_invalid_row_kind(tmp_path) -> None:
    payload = {
        "summary": ["repo=test"],
        "invariants": {"passed": True},
        "quality_gates": {"threshold_profile": "single_language"},
        "per_node": [
            {
                "entity": "fixture.sample.entry",
                "language": "python",
                "kind": "callable",
                "file_path": "sample.py",
                "module_qualified_name": "fixture.sample",
            }
        ],
    }
    out = tmp_path / "report.json"
    with pytest.raises(ValueError) as exc:
        write_json(out, payload)
    assert "kind" in str(exc.value)
