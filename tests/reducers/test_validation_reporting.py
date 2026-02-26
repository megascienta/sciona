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


def test_render_summary_includes_action_and_reason_sections() -> None:
    payload = {
        "summary": ["repo=test", "sampled_nodes=1", "invariants_passed=True"],
        "validation_workflow_goals": {
            "a": "internal consistency",
            "b": "strict overlap",
            "c": "boundary envelope",
        },
        "core_metrics": {"static_contract_recall": 1.0, "static_overreach_rate": 0.0},
        "invariants": {"passed": True, "hard_passed": True},
        "quality_gates": {"threshold_profile": "single_language"},
        "internal_integrity": {"valid": True, "projection": {}, "determinism": {}},
        "static_contract_alignment": {
            "static_contract_precision": 0.9,
            "static_contract_recall": 0.95,
            "static_overreach_rate": 0.1,
        },
        "enriched_truth_alignment": {
            "tiers": {"full": {"reducer_precision": 0.8, "reducer_recall": 0.7}},
        },
        "contract_boundary": {
            "limitation_edge_counts": {
                "independent_static_limitation_edges": 2,
                "contract_exclusion_edges": 3,
                "included_limitation_edges": 2,
                "excluded_out_of_scope_edges": 3,
            },
            "contract_leakage_rate": {"overall": 0.1, "by_reason": {"dynamic": 0.1}},
        },
        "parity_attribution": {
            "repo_totals": {
                "independent_candidate_set": {"candidate_pressure": 3},
                "core_selector": {"selector_pressure": 1},
                "final_edge_parity": {"core_overresolution": 2},
                "row_dominant_cause": {"core_selector_gap_dominant": 1},
            }
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
        "strict_contract_diagnostics": {"accepted_by_provenance": {"exact_qname": 1}},
        "metric_definitions": {},
        "report_schema_version": "test",
        "action_priority_board": [{"priority": "high", "area": "core", "issue": "x", "evidence": {}}],
    }
    lines = render_summary(payload)
    text = "\n".join(lines)
    assert "## Validation Goals" in text
    assert "## Run Verdict" in text
    assert "## Mismatch Source" in text
    assert "## Contract Boundary" in text
    assert "## Top Risks" in text
    assert "## Appendix" in text


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
