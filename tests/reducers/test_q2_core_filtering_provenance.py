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
                "metrics_reducer_vs_db": {"tp": 1, "fp": 0, "fn": 0},
                "metrics_reducer_vs_contract": {"tp": 1, "fp": 0, "fn": 0},
                "metrics_db_vs_contract": {"tp": 1, "fp": 0, "fn": 0},
                "contract_truth_edges": [{"caller": "fixture.mod.fn", "callee": "helper"}],
            }
        ],
        out_of_contract_meta=[],
    )
    assert payload["questions"]["q2"]["filtering_source"] == "core_only"
    assert payload["quality_gates"]["q2_filtering_source"] == "core_only"


def test_q2_filtering_pipeline_no_validation_contract_override() -> None:
    base = Path("validations/reducers/validation")
    call_contract_text = (base / "call_contract.py").read_text(encoding="utf-8")
    orchestrator_text = (base / "orchestrator.py").read_text(encoding="utf-8")
    out_of_contract_text = (base / "out_of_contract.py").read_text(encoding="utf-8")
    assert (
        "from sciona.code_analysis.contracts import select_strict_call_candidate"
        in call_contract_text
    )
    assert "get_validation_contract" not in orchestrator_text
    assert "def standard_call_names" not in out_of_contract_text
