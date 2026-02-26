# SPDX-License-Identifier: MIT

from validations.reducers.validation.invariants import (
    basket_split_checks,
    evaluate_invariants,
    filter_contract_checks,
)


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
        basket_partition_ok=True,
        basket_counts_reconciled_ok=True,
        typescript_relative_index_contract_ok=True,
        class_truth_nonempty_rate_ok=True,
        class_truth_match_rate_ok=True,
        scoped_call_normalization_ok=True,
        strict_contract_parity_ok=True,
        limitation_scope_clean_ok=True,
        limitation_taxonomy_stable_ok=True,
        strict_drop_taxonomy_stable_ok=True,
        kind_precision_floors_ok=True,
        contract_recall_ok=True,
        overreach_rate_ok=True,
        member_call_recall_ok=None,
    )
    assert inv["gate_member_call_recall_min"] is None
    assert inv["gate_strict_contract_parity"] is True
    assert inv["passed"] is True


def test_strict_contract_parity_gate_fails_hard() -> None:
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
        basket_partition_ok=True,
        basket_counts_reconciled_ok=True,
        typescript_relative_index_contract_ok=True,
        class_truth_nonempty_rate_ok=True,
        class_truth_match_rate_ok=True,
        scoped_call_normalization_ok=True,
        strict_contract_parity_ok=False,
        limitation_scope_clean_ok=True,
        limitation_taxonomy_stable_ok=True,
        strict_drop_taxonomy_stable_ok=True,
        kind_precision_floors_ok=True,
        contract_recall_ok=True,
        overreach_rate_ok=True,
        member_call_recall_ok=None,
    )
    assert inv["gate_strict_contract_parity"] is False
    assert inv["hard_passed"] is False


def test_limitation_taxonomy_gate_fails_hard() -> None:
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
        basket_partition_ok=True,
        basket_counts_reconciled_ok=True,
        typescript_relative_index_contract_ok=True,
        class_truth_nonempty_rate_ok=True,
        class_truth_match_rate_ok=True,
        scoped_call_normalization_ok=True,
        strict_contract_parity_ok=True,
        limitation_scope_clean_ok=False,
        limitation_taxonomy_stable_ok=False,
        strict_drop_taxonomy_stable_ok=False,
        kind_precision_floors_ok=True,
        contract_recall_ok=True,
        overreach_rate_ok=True,
        member_call_recall_ok=None,
    )
    assert inv["gate_limitation_scope_clean"] is False
    assert inv["gate_limitation_taxonomy_stable"] is False
    assert inv["gate_strict_drop_taxonomy_stable"] is False
    assert inv["hard_passed"] is False


def test_kind_precision_floor_gate_is_diagnostic() -> None:
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
        basket_partition_ok=True,
        basket_counts_reconciled_ok=True,
        typescript_relative_index_contract_ok=True,
        class_truth_nonempty_rate_ok=True,
        class_truth_match_rate_ok=True,
        scoped_call_normalization_ok=True,
        strict_contract_parity_ok=True,
        limitation_scope_clean_ok=True,
        limitation_taxonomy_stable_ok=True,
        strict_drop_taxonomy_stable_ok=True,
        kind_precision_floors_ok=False,
        contract_recall_ok=True,
        overreach_rate_ok=True,
        member_call_recall_ok=None,
    )
    assert inv["gate_kind_precision_floors"] is False
    assert inv["hard_passed"] is True
    assert "kind precision floor gate failed" in (inv.get("diagnostic_failures") or [])


def test_filter_contract_checks_rejects_unresolved_contract_edges() -> None:
    rows = [
        {
            "contract_truth_edges": [
                {"caller": "a", "callee": "x", "callee_qname": None},
            ],
            "independent_static_limitation_edges": [],
        }
    ]
    pure_ok, resolved_ok, dedupe_ok = filter_contract_checks(rows)
    assert pure_ok is True
    assert resolved_ok is False
    assert dedupe_ok is True


def test_filter_contract_checks_rejects_contract_enrichment_overlap() -> None:
    edge = {"caller": "a", "callee": "x", "callee_qname": "pkg.x"}
    rows = [{"contract_truth_edges": [edge], "independent_static_limitation_edges": [edge]}]
    pure_ok, resolved_ok, dedupe_ok = filter_contract_checks(rows)
    assert pure_ok is False
    assert resolved_ok is True
    assert dedupe_ok is True


def test_basket_split_checks_rejects_overlap_between_limitation_and_exclusion() -> None:
    edge = {"caller": "a", "callee": "x", "callee_qname": "pkg.x"}
    rows = [
        {
            "contract_truth_edges": [],
            "independent_static_limitation_edges": [edge],
            "contract_exclusion_edges": [edge],
            "included_limitation_count": 1,
            "excluded_out_of_scope_count": 1,
        }
    ]
    partition_ok, counts_ok = basket_split_checks(rows)
    assert partition_ok is False
    assert counts_ok is True


def test_basket_split_checks_rejects_count_mismatch() -> None:
    rows = [
        {
            "contract_truth_edges": [],
            "independent_static_limitation_edges": [
                {"caller": "a", "callee": "x", "callee_qname": "pkg.x"}
            ],
            "contract_exclusion_edges": [],
            "included_limitation_count": 0,
            "excluded_out_of_scope_count": 0,
        }
    ]
    partition_ok, counts_ok = basket_split_checks(rows)
    assert partition_ok is True
    assert counts_ok is False
