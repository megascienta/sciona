# SPDX-License-Identifier: MIT

from experiments.reducers.validation.invariants import evaluate_invariants, filter_contract_checks


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


def test_filter_contract_checks_rejects_unresolved_contract_edges() -> None:
    rows = [
        {
            "contract_truth_edges": [
                {"caller": "a", "callee": "x", "callee_qname": None},
            ],
            "enrichment_edges": [],
        }
    ]
    pure_ok, resolved_ok, dedupe_ok = filter_contract_checks(rows)
    assert pure_ok is True
    assert resolved_ok is False
    assert dedupe_ok is True


def test_filter_contract_checks_rejects_contract_enrichment_overlap() -> None:
    edge = {"caller": "a", "callee": "x", "callee_qname": "pkg.x"}
    rows = [{"contract_truth_edges": [edge], "enrichment_edges": [edge]}]
    pure_ok, resolved_ok, dedupe_ok = filter_contract_checks(rows)
    assert pure_ok is False
    assert resolved_ok is True
    assert dedupe_ok is True
