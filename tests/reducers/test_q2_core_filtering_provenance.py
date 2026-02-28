# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from validations.reducers.validation.orchestrator import _build_report_payload


def test_q2_payload_declares_core_only_filtering_source(tmp_path: Path) -> None:
    payload = _build_report_payload(
        repo_root=tmp_path,
        rows=[
            {
                "entity": "fixture.mod.fn",
                "language": "python",
                "kind": "function",
                "file_path": "mod.py",
                "module_qualified_name": "fixture.mod",
                "set_q1_reducer_vs_db": {
                    "reference_count": 1,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                },
                "set_q2_reducer_vs_independent_contract": {
                    "reference_count": 1,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                    "match_provenance_breakdown": {"qname_exact": 1},
                },
            }
        ],
        out_of_contract_meta=[],
    )
    assert payload["questions"]["q2"]["filtering_source"] == "core_only"
    assert payload["quality_gates"]["q2_filtering_source"] == "core_only"
    assert payload["invariants"]["pipeline_self_consistent"] is True
    assert payload["invariants"]["independently_verified"] is True
    assert payload["invariants"]["passed"] is True
    assert payload["questions"]["q2"]["envelope_reference_count"] == 1
    assert payload["questions"]["q2"]["envelope_excluded_count"] == 0
    assert payload["questions"]["q2"]["envelope_total_count"] == 1
    assert payload["questions"]["q2"]["contract_filtered_out_ratio"] == 0.0
    assert payload["questions"]["q2"]["match_provenance_breakdown"] == {"qname_exact": 1}
    assert payload["questions"]["q2"]["strict_contract_candidate_count_histogram"] == {}


def test_q2_filtering_pipeline_no_validation_contract_override() -> None:
    base = Path("validations/reducers/validation")
    assert not (base / "contract_spec.py").exists()
    call_contract_text = (base / "call_contract.py").read_text(encoding="utf-8")
    import_contract_text = (base / "import_contract.py").read_text(encoding="utf-8")
    orchestrator_text = (base / "orchestrator.py").read_text(encoding="utf-8")
    out_of_contract_text = (base / "out_of_contract.py").read_text(encoding="utf-8")
    assert (
        "from sciona.code_analysis.contracts import select_strict_call_candidate"
        in call_contract_text
    )
    assert "from .independent.contract_normalization import" not in import_contract_text
    assert "core_normalize_python_import" in import_contract_text
    assert "core_normalize_typescript_import" in import_contract_text
    assert "get_validation_contract" not in orchestrator_text
    assert "def standard_call_names" not in out_of_contract_text


def test_q3_payload_includes_provenance_breakdown(tmp_path: Path) -> None:
    payload = _build_report_payload(
        repo_root=tmp_path,
        rows=[
            {
                "entity": "fixture.mod.fn",
                "language": "python",
                "kind": "function",
                "file_path": "mod.py",
                "module_qualified_name": "fixture.mod",
                "set_q1_reducer_vs_db": {
                    "reference_count": 1,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                },
                "set_q2_reducer_vs_independent_contract": {
                    "reference_count": 1,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                },
                "basket2_edges": [{"caller": "fixture.mod.fn", "callee": "invoke"}],
            }
        ],
        out_of_contract_meta=[
            {
                "edge_type": "call",
                "language": "python",
                "reason": "dynamic",
                "semantic_type": "dynamic_call",
                "entity": "fixture.mod.fn",
                "entity_kind": "function",
                "caller": "fixture.mod.fn",
                "callee": "invoke",
                "callee_qname": None,
                "provenance": "syntax_raw",
            }
        ],
    )
    q3 = payload["questions"]["q3"]
    assert q3["by_semantic_type_non_static_avg_rate"] == {"dynamic_call": 1.0}
    assert q3["by_semantic_type_non_static_avg_percent"] == {"dynamic_call": 100.0}
    assert q3["decorator_rate_percent"] == 0.0
    assert q3["dynamic_dispatch_rate_percent"] == 100.0


def test_q3_payload_separates_decorator_and_dynamic_rates(tmp_path: Path) -> None:
    payload = _build_report_payload(
        repo_root=tmp_path,
        rows=[
            {
                "entity": "fixture.mod.fn",
                "language": "python",
                "kind": "function",
                "file_path": "mod.py",
                "module_qualified_name": "fixture.mod",
                "set_q1_reducer_vs_db": {
                    "reference_count": 1,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                },
                "set_q2_reducer_vs_independent_contract": {
                    "reference_count": 2,
                    "candidate_count": 2,
                    "intersection_count": 2,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                },
            }
        ],
        out_of_contract_meta=[
            {
                "edge_type": "call",
                "language": "python",
                "reason": "dynamic",
                "semantic_type": "dynamic_call",
                "entity": "fixture.mod.fn",
                "entity_kind": "function",
                "caller": "fixture.mod.fn",
                "callee": "invoke",
                "callee_qname": None,
                "provenance": "syntax_raw",
            },
            {
                "edge_type": "call",
                "language": "python",
                "reason": "decorator",
                "semantic_type": "decorator_call",
                "entity": "fixture.mod.fn",
                "entity_kind": "function",
                "caller": "fixture.mod.fn",
                "callee": "cache",
                "callee_qname": None,
                "provenance": "syntax_raw",
            },
        ],
    )
    q3 = payload["questions"]["q3"]
    assert q3["avg_non_static_rate_percent"] == 100.0
    assert q3["decorator_rate_percent"] == 50.0
    assert q3["dynamic_dispatch_rate_percent"] == 50.0


def test_unresolved_static_is_reported_as_separate_defect(tmp_path: Path) -> None:
    payload = _build_report_payload(
        repo_root=tmp_path,
        rows=[
            {
                "entity": "fixture.mod.fn",
                "language": "python",
                "kind": "function",
                "file_path": "mod.py",
                "module_qualified_name": "fixture.mod",
                "set_q1_reducer_vs_db": {
                    "reference_count": 1,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                },
                "set_q2_reducer_vs_independent_contract": {
                    "reference_count": 2,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 1,
                    "spillover_count": 0,
                    "coverage": 0.5,
                    "spillover_ratio": 0.0,
                },
                "basket2_edges": [{"caller": "fixture.mod.fn", "callee": "helper"}],
            }
        ],
        out_of_contract_meta=[
            {
                "edge_type": "call",
                "language": "python",
                "reason": "in_repo_unresolved",
                "semantic_type": "direct_call_unresolved",
                "entity": "fixture.mod.fn",
                "entity_kind": "function",
                "caller": "fixture.mod.fn",
                "callee": "helper",
                "callee_qname": None,
                "provenance": "syntax_raw",
            }
        ],
    )
    unresolved = payload["questions"]["q3"]["unresolved_static_defect"]
    assert unresolved["pass"] is False
    assert unresolved["avg_rate_percent"] == 50.0
    assert unresolved["by_semantic_type_avg_percent"] == {"direct_call_unresolved": 50.0}
    q2 = payload["questions"]["q2"]
    assert q2["envelope_reference_count"] == 2
    assert q2["envelope_excluded_count"] == 0
    assert q2["contract_filtered_out_ratio"] == 0.0


def test_q2_payload_reports_contract_filtered_out_ratio(tmp_path: Path) -> None:
    payload = _build_report_payload(
        repo_root=tmp_path,
        rows=[
            {
                "entity": "fixture.mod.fn",
                "language": "python",
                "kind": "function",
                "file_path": "mod.py",
                "module_qualified_name": "fixture.mod",
                "set_q1_reducer_vs_db": {
                    "reference_count": 1,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                },
                "set_q2_reducer_vs_independent_contract": {
                    "reference_count": 3,
                    "candidate_count": 3,
                    "intersection_count": 3,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                    "match_provenance_breakdown": {"name_only": 1, "qname_suffix": 2},
                },
                "q2_filtering_stats": {
                    "reference_in_contract_count": 3,
                    "excluded_out_of_scope_count": 2,
                    "excluded_limitation_count": 1,
                    "excluded_total_count": 3,
                    "excluded_out_of_scope_by_reason": {"external": 2},
                    "excluded_limitation_by_reason": {"dynamic": 1},
                },
                "q2_ground_truth_diagnostics": {
                    "strict_contract_candidate_count_histogram": {"0": 2, "1": 1}
                },
            }
        ],
        out_of_contract_meta=[],
    )
    q2 = payload["questions"]["q2"]
    assert q2["envelope_reference_count"] == 3
    assert q2["envelope_excluded_count"] == 3
    assert q2["envelope_total_count"] == 6
    assert q2["contract_filtered_out_ratio"] == 0.5
    assert q2["envelope_excluded_by_reason"] == {"dynamic": 1, "external": 2}
    assert q2["match_provenance_breakdown"] == {"name_only": 1, "qname_suffix": 2}
    assert q2["strict_contract_candidate_count_histogram"] == {"0": 2, "1": 1}


def test_q2_reports_class_truth_reliability_breakdown(tmp_path: Path) -> None:
    payload = _build_report_payload(
        repo_root=tmp_path,
        rows=[
            {
                "entity": "fixture.mod.A",
                "language": "python",
                "kind": "class",
                "file_path": "mod.py",
                "module_qualified_name": "fixture.mod",
                "set_q1_reducer_vs_db": {
                    "reference_count": 0,
                    "candidate_count": 0,
                    "intersection_count": 0,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": None,
                    "spillover_ratio": None,
                },
                "set_q2_reducer_vs_independent_contract": {
                    "reference_count": 1,
                    "candidate_count": 1,
                    "intersection_count": 1,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": 1.0,
                    "spillover_ratio": 0.0,
                },
                "q2_ground_truth_diagnostics": {
                    "class_truth_unreliable": False,
                    "class_match_strategy": "exact_qname",
                    "class_candidate_count": 1,
                    "class_truth_method_count": 1,
                },
            },
            {
                "entity": "fixture.mod.B",
                "language": "python",
                "kind": "class",
                "file_path": "mod.py",
                "module_qualified_name": "fixture.mod",
                "set_q1_reducer_vs_db": {
                    "reference_count": 0,
                    "candidate_count": 0,
                    "intersection_count": 0,
                    "missing_count": 0,
                    "spillover_count": 0,
                    "coverage": None,
                    "spillover_ratio": None,
                },
                "set_q2_reducer_vs_independent_contract": None,
                "q2_ground_truth_diagnostics": {
                    "class_truth_unreliable": True,
                    "class_match_strategy": "ambiguous",
                    "class_candidate_count": 2,
                    "class_truth_method_count": 0,
                },
            },
        ],
        out_of_contract_meta=[],
    )
    q2 = payload["questions"]["q2"]
    assert q2["class_truth_unreliable_count"] == 1
    assert q2["class_truth_unreliable_scored_excluded_count"] == 1
    assert q2["class_match_strategy_breakdown"] == {"ambiguous": 1, "exact_qname": 1}
