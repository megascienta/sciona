# SPDX-License-Identifier: MIT

from experiments.reducers.validation.invariants import evaluate_invariants


def test_member_call_recall_gate_is_not_failing_when_not_applicable() -> None:
    inv = evaluate_invariants(
        rows=[],
        reducer_full_entities=set(),
        db_full_entities=set(),
        reducer_full_micro={"tp": 0, "fp": 0, "fn": 0},
        db_full_micro={"tp": 0, "fp": 0, "fn": 0},
        parse_ok_files=0,
        total_files=0,
        contract_truth_pure_ok=True,
        contract_truth_resolved_ok=True,
        parser_deterministic=True,
        no_duplicate_contract_edges=True,
        typescript_relative_index_contract_ok=True,
        class_truth_nonempty_rate_ok=True,
        class_truth_match_rate_ok=True,
        scoped_call_normalization_ok=True,
        contract_recall_ok=True,
        overreach_rate_ok=True,
        member_call_recall_ok=None,
    )
    assert inv["gate_member_call_recall_min"] is None
    assert inv["passed"] is True
