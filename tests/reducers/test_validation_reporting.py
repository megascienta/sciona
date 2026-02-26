# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from validations.reducers.validation.orchestrator import (
    _bootstrap_micro_ci,
    _select_threshold_profile,
    _strict_contract_policy_violations,
)
from validations.reducers.validation.report import render_summary, write_json


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


def test_render_summary_includes_only_three_core_questions() -> None:
    payload = {
        "summary": ["repo=test", "sampled_nodes=1", "invariants_passed=True"],
        "invariants": {"passed": True, "hard_passed": True},
        "quality_gates": {"threshold_profile": "single_language"},
        "questions": {
            "q1": {
                "pass": True,
                "exact_required": True,
                "tp": 100,
                "fp": 0,
                "fn": 0,
                "mismatch_nodes": 0,
            },
            "q2": {
                "pass": True,
                "target": 0.99,
                "precision": 1.0,
                "recall": 1.0,
                "fp": 0,
                "fn": 0,
                "contract_truth_edges": 200,
            },
            "q3": {
                "descriptive_only": True,
                "total_edges": 20,
                "uplift_vs_contract_truth": 0.1,
                "by_reason": {"dynamic_call": 10, "decorator": 10},
                "by_reason_percent": {"dynamic_call": 0.5, "decorator": 0.5},
                "by_edge_type": {"call": 20},
            },
        },
        "per_node": [],
        "report_schema_version": "test",
    }
    lines = render_summary(payload)
    text = "\n".join(lines)
    assert "## Q1. Reducers vs DB Correctness" in text
    assert "## Q2. Reducers vs Independent Within Static Contract" in text
    assert "## Q3. Beyond Static Contract Envelope" in text
    assert "## Validation Goals" not in text
    assert "## Run Verdict" not in text


def test_strict_contract_policy_violations_detects_mode_and_key_drift() -> None:
    rows = [
        {
            "strict_contract_mode": "candidate_only_strict_contract_v2",
            "strict_contract_accepted_by_provenance": {"exact_qname": 2, "new_source": 1},
            "strict_contract_dropped_by_reason": {"no_candidates": 3, "new_reason": 4},
        }
    ]
    violations = _strict_contract_policy_violations(
        rows,
        mode="candidate_only_strict_contract_v1",
        allowed_acceptance={"exact_qname"},
        allowed_drop_reasons={"no_candidates"},
    )
    assert violations["mode_mismatch_count"] == 1
    assert violations["accepted_violations"] == {"new_source": 1}
    assert violations["dropped_violations"] == {"new_reason": 4}


def test_strict_contract_policy_violations_accepts_known_keys() -> None:
    rows = [
        {
            "strict_contract_mode": "candidate_only_strict_contract_v1",
            "strict_contract_accepted_by_provenance": {"exact_qname": 2},
            "strict_contract_dropped_by_reason": {"no_candidates": 3},
        }
    ]
    violations = _strict_contract_policy_violations(
        rows,
        mode="candidate_only_strict_contract_v1",
        allowed_acceptance={"exact_qname"},
        allowed_drop_reasons={"no_candidates"},
    )
    assert violations["mode_mismatch_count"] == 0
    assert violations["accepted_violations"] == {}
    assert violations["dropped_violations"] == {}


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
