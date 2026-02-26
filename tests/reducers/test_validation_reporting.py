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
