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
                },
            }
        ],
        out_of_contract_meta=[],
    )
    assert payload["questions"]["q2"]["filtering_source"] == "core_only"
    assert payload["quality_gates"]["q2_filtering_source"] == "core_only"


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
    assert q3["by_semantic_type"] == {"dynamic_call": 1}
    assert q3["by_semantic_type_percent"] == {"dynamic_call": 100.0}
