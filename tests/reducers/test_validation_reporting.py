# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from validations.reducers.validation.report import render_summary, write_json


def test_render_summary_includes_only_three_core_questions() -> None:
    payload = {
        "summary": ["repo=test", "sampled_nodes=1", "invariants_passed=True"],
        "invariants": {"passed": True, "hard_passed": True},
        "quality_gates": {"threshold_profile": "single_language"},
        "questions": {
            "q1": {
                "pass": True,
                "exact_required": True,
                "reference_count": 100,
                "candidate_count": 100,
                "intersection_count": 100,
                "missing_count": 0,
                "spillover_count": 0,
                "mismatch_nodes": 0,
            },
            "q2": {
                "pass": True,
                "target_mutual_accuracy_min": 0.99,
                "target_missing_rate_max": 0.01,
                "target_spillover_rate_max": 0.01,
                "scored_nodes": 1,
                "avg_missing_rate": 0.0,
                "avg_spillover_rate": 0.0,
                "avg_mutual_accuracy": 1.0,
                "reference_count": 200,
                "candidate_count": 200,
                "intersection_count": 200,
                "missing_count": 0,
                "spillover_count": 0,
                "by_language": {
                    "python": {
                        "scored_nodes": 1,
                        "avg_missing_rate": 0.0,
                        "avg_spillover_rate": 0.0,
                        "avg_mutual_accuracy": 1.0,
                        "pass": True,
                    }
                },
                "filtering_source": "core_only",
            },
            "q3": {
                "descriptive_only": True,
                "scored_nodes": 1,
                "total_non_static_edges": 20,
                "avg_non_static_rate_percent": 10.0,
                "by_semantic_type_non_static_avg_percent": {
                    "dynamic_call": 50.0,
                    "dynamic_member_call": 50.0,
                },
                "unresolved_static_defect": {
                    "target_zero": True,
                    "pass": True,
                    "avg_rate_percent": 0.0,
                },
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
                "set_q1_reducer_vs_db": {
                    "reference_count": 1,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                },
                "basket2_edges": [],
                "q2_node_rates": None,
                "q3_non_static_rate_percent": None,
                "unresolved_static_rate_percent": None,
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


def test_write_json_rejects_legacy_metric_keys(tmp_path) -> None:
    payload = {
        "summary": ["repo=test"],
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
    with pytest.raises(ValueError) as exc:
        write_json(out, payload)
    assert "not allowed in current schema" in str(exc.value)
