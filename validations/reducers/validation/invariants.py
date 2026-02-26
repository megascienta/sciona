# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import List, Tuple

def edge_key(edge: dict) -> Tuple[str, str]:
    caller = edge.get("caller") or ""
    target = edge.get("callee_qname") or edge.get("callee") or ""
    return caller, target


def edge_full_key(edge: dict) -> Tuple[str, str, str | None]:
    return (
        edge.get("caller") or "",
        edge.get("callee") or "",
        edge.get("callee_qname"),
    )


def edge_set(edges: List[dict]) -> set[Tuple[str, str]]:
    return {edge_key(edge) for edge in edges}


def edge_full_set(edges: List[dict]) -> set[Tuple[str, str, str | None]]:
    return {edge_full_key(edge) for edge in edges}


def filter_contract_checks(rows: List[dict]) -> tuple[bool, bool, bool]:
    contract_truth_pure_ok = True
    contract_truth_resolved_ok = True
    no_duplicate_contract_edges = True
    for row in rows:
        contract_edges = row.get("contract_truth_edges") or []
        limitation_edges = row.get("independent_static_limitation_edges") or []
        if len(edge_full_set(contract_edges)) != len(contract_edges):
            no_duplicate_contract_edges = False
            break
        if len(edge_full_set(limitation_edges)) != len(limitation_edges):
            no_duplicate_contract_edges = False
            break
        contract_keys = edge_full_set(contract_edges)
        limitation_keys = edge_full_set(limitation_edges)
        if contract_keys & limitation_keys:
            contract_truth_pure_ok = False
            break
        for edge in contract_edges:
            if not edge.get("callee_qname"):
                contract_truth_resolved_ok = False
                break
        if not contract_truth_resolved_ok:
            break
    return contract_truth_pure_ok, contract_truth_resolved_ok, no_duplicate_contract_edges


def basket_split_checks(rows: List[dict]) -> tuple[bool, bool]:
    basket_partition_ok = True
    basket_counts_reconciled_ok = True
    for row in rows:
        contract_edges = row.get("contract_truth_edges") or []
        limitation_edges = row.get("independent_static_limitation_edges") or []
        exclusion_edges = row.get("contract_exclusion_edges") or []
        contract_keys = edge_full_set(contract_edges)
        limitation_keys = edge_full_set(limitation_edges)
        exclusion_keys = edge_full_set(exclusion_edges)
        if contract_keys & limitation_keys:
            basket_partition_ok = False
            break
        if contract_keys & exclusion_keys:
            basket_partition_ok = False
            break
        if limitation_keys & exclusion_keys:
            basket_partition_ok = False
            break
        if int(row.get("included_limitation_count") or 0) != len(limitation_keys):
            basket_counts_reconciled_ok = False
            break
        if int(row.get("excluded_out_of_scope_count") or 0) != len(exclusion_keys):
            basket_counts_reconciled_ok = False
            break
    return basket_partition_ok, basket_counts_reconciled_ok


def basket_split_diagnostics(rows: List[dict], *, sample_limit: int = 10) -> dict:
    overlap_counts = {
        "contract_vs_limitation": 0,
        "contract_vs_exclusion": 0,
        "limitation_vs_exclusion": 0,
    }
    count_mismatches = {
        "included_limitation_count_mismatch": 0,
        "excluded_out_of_scope_count_mismatch": 0,
    }
    overlap_examples: list[dict] = []
    count_examples: list[dict] = []

    for row in rows:
        contract_edges = row.get("contract_truth_edges") or []
        limitation_edges = row.get("independent_static_limitation_edges") or []
        exclusion_edges = row.get("contract_exclusion_edges") or []
        contract_keys = edge_full_set(contract_edges)
        limitation_keys = edge_full_set(limitation_edges)
        exclusion_keys = edge_full_set(exclusion_edges)

        overlap_cl = contract_keys & limitation_keys
        overlap_ce = contract_keys & exclusion_keys
        overlap_le = limitation_keys & exclusion_keys
        if overlap_cl:
            overlap_counts["contract_vs_limitation"] += len(overlap_cl)
        if overlap_ce:
            overlap_counts["contract_vs_exclusion"] += len(overlap_ce)
        if overlap_le:
            overlap_counts["limitation_vs_exclusion"] += len(overlap_le)
        if (overlap_cl or overlap_ce or overlap_le) and len(overlap_examples) < sample_limit:
            overlap_examples.append(
                {
                    "entity": row.get("entity"),
                    "language": row.get("language"),
                    "kind": row.get("kind"),
                    "overlap_edge_counts": {
                        "contract_vs_limitation": len(overlap_cl),
                        "contract_vs_exclusion": len(overlap_ce),
                        "limitation_vs_exclusion": len(overlap_le),
                    },
                }
            )

        included_expected = int(row.get("included_limitation_count") or 0)
        excluded_expected = int(row.get("excluded_out_of_scope_count") or 0)
        included_actual = len(limitation_keys)
        excluded_actual = len(exclusion_keys)
        included_mismatch = included_expected != included_actual
        excluded_mismatch = excluded_expected != excluded_actual
        if included_mismatch:
            count_mismatches["included_limitation_count_mismatch"] += 1
        if excluded_mismatch:
            count_mismatches["excluded_out_of_scope_count_mismatch"] += 1
        if (included_mismatch or excluded_mismatch) and len(count_examples) < sample_limit:
            count_examples.append(
                {
                    "entity": row.get("entity"),
                    "language": row.get("language"),
                    "kind": row.get("kind"),
                    "included_limitation_count": {
                        "expected": included_expected,
                        "actual": included_actual,
                    },
                    "excluded_out_of_scope_count": {
                        "expected": excluded_expected,
                        "actual": excluded_actual,
                    },
                }
            )

    partition_ok = all(value == 0 for value in overlap_counts.values())
    counts_reconciled_ok = all(value == 0 for value in count_mismatches.values())
    return {
        "partition_ok": partition_ok,
        "counts_reconciled_ok": counts_reconciled_ok,
        "overlap_counts": overlap_counts,
        "count_mismatches": count_mismatches,
        "overlap_examples": overlap_examples,
        "count_examples": count_examples,
    }


def evaluate_invariants(
    rows: List[dict],
    *,
    reducer_full_entities: set[str],
    db_full_entities: set[str],
    reducer_full_micro: dict,
    db_full_micro: dict,
    parse_ok_files: int,
    total_files: int,
    contract_truth_pure_ok: bool,
    contract_truth_resolved_ok: bool,
    parser_deterministic: bool,
    no_duplicate_contract_edges: bool,
    basket_partition_ok: bool,
    basket_counts_reconciled_ok: bool,
    typescript_relative_index_contract_ok: bool,
    class_truth_nonempty_rate_ok: bool,
    class_truth_match_rate_ok: bool,
    scoped_call_normalization_ok: bool,
    strict_contract_parity_ok: bool,
    limitation_scope_clean_ok: bool,
    limitation_taxonomy_stable_ok: bool,
    strict_drop_taxonomy_stable_ok: bool,
    kind_precision_floors_ok: bool,
    contract_recall_ok: bool,
    overreach_rate_ok: bool,
    member_call_recall_ok: bool | None,
) -> dict:
    hard_failures: List[str] = []
    diagnostic_failures: List[str] = []
    exact_mismatches: List[dict] = []
    comparable_rows = [
        row for row in rows if not row.get("reducer_error") and not row.get("db_error")
    ]
    for row in comparable_rows:
        reducer_set = edge_set(row.get("reducer_edges") or [])
        db_set = edge_set(row.get("db_edges") or [])
        if reducer_set != db_set:
            exact_mismatches.append(
                {
                    "entity": row["entity"],
                    "reducer_only": sorted(reducer_set - db_set)[:5],
                    "db_only": sorted(db_set - reducer_set)[:5],
                }
            )
    gate_reducer_db_exact = len(exact_mismatches) == 0
    if not gate_reducer_db_exact:
        hard_failures.append(f"reducer/db exact mismatch on {len(exact_mismatches)} nodes")

    gate_aligned_scoring = reducer_full_entities == db_full_entities
    if not gate_aligned_scoring:
        only_reducer = sorted(reducer_full_entities - db_full_entities)[:10]
        only_db = sorted(db_full_entities - reducer_full_entities)[:10]
        hard_failures.append(
            f"full scoring set misaligned: reducer_only={only_reducer}, db_only={only_db}"
        )

    gate_parse_coverage = (parse_ok_files == total_files)
    if not gate_parse_coverage:
        hard_failures.append(f"independent parser parse coverage is {parse_ok_files}/{total_files}, expected full coverage")

    gate_contract_truth_pure = contract_truth_pure_ok
    if not gate_contract_truth_pure:
        hard_failures.append("contract truth overlaps with enrichment edges")
    gate_contract_truth_resolved = contract_truth_resolved_ok
    if not gate_contract_truth_resolved:
        hard_failures.append("contract truth contains unresolved targets")
    gate_parser_deterministic = parser_deterministic
    if not gate_parser_deterministic:
        hard_failures.append("independent parser output is non-deterministic across repeated runs")
    gate_no_duplicate_contract_edges = no_duplicate_contract_edges
    if not gate_no_duplicate_contract_edges:
        hard_failures.append("duplicate edges detected in filtered or full independent truth")
    gate_basket_partition = basket_partition_ok
    if not gate_basket_partition:
        hard_failures.append("basket partition violated: contract/limitation/exclusion overlap detected")
    gate_basket_counts_reconciled = basket_counts_reconciled_ok
    if not gate_basket_counts_reconciled:
        hard_failures.append("basket count reconciliation failed for included/excluded limitation counts")
    gate_typescript_relative_index_contract = typescript_relative_index_contract_ok
    if not gate_typescript_relative_index_contract:
        diagnostic_failures.append(
            "typescript import contract parity failed: relative import index fallback mismatch"
        )
    gate_class_truth_nonempty_rate = class_truth_nonempty_rate_ok
    if not gate_class_truth_nonempty_rate:
        diagnostic_failures.append(
            "class truth quality gate failed: too many class nodes have empty contract truth with parse_ok"
        )
    gate_class_truth_match_rate = class_truth_match_rate_ok
    if not gate_class_truth_match_rate:
        diagnostic_failures.append(
            "class truth match-rate gate failed: too many class rows have unreliable class mapping"
        )
    gate_scoped_call_normalization = scoped_call_normalization_ok
    if not gate_scoped_call_normalization:
        hard_failures.append(
            "scoped call normalization gate failed: ambiguous terminals remain mapped to multiple qnames"
        )
    gate_strict_contract_parity = strict_contract_parity_ok
    if not gate_strict_contract_parity:
        hard_failures.append(
            "strict contract parity gate failed: independent strict acceptance includes out-of-contract provenance/reasons"
        )
    gate_limitation_scope_clean = limitation_scope_clean_ok
    if not gate_limitation_scope_clean:
        hard_failures.append("independent limitation scope gate failed: out-of-scope reasons leaked into limitation basket")
    gate_limitation_taxonomy_stable = limitation_taxonomy_stable_ok
    if not gate_limitation_taxonomy_stable:
        hard_failures.append("independent limitation taxonomy gate failed: unknown limitation reasons detected")
    gate_strict_drop_taxonomy_stable = strict_drop_taxonomy_stable_ok
    if not gate_strict_drop_taxonomy_stable:
        hard_failures.append("strict drop taxonomy gate failed: unknown dropped reasons detected")
    gate_kind_precision_floors = kind_precision_floors_ok
    if not gate_kind_precision_floors:
        diagnostic_failures.append("kind precision floor gate failed")
    gate_contract_recall_min = contract_recall_ok
    if not gate_contract_recall_min:
        diagnostic_failures.append("contract recall quality gate failed")
    gate_overreach_rate_max = overreach_rate_ok
    if not gate_overreach_rate_max:
        diagnostic_failures.append("overreach-rate quality gate failed")
    gate_member_call_recall_min = member_call_recall_ok
    if gate_member_call_recall_min is False:
        diagnostic_failures.append("member-call recall quality gate failed")

    gate_equal_contract_metrics = True
    if gate_reducer_db_exact and gate_aligned_scoring:
        for key in ("tp", "fp", "fn"):
            if reducer_full_micro.get(key) != db_full_micro.get(key):
                gate_equal_contract_metrics = False
                break
        if not gate_equal_contract_metrics:
            hard_failures.append(
                f"reducer_vs_contract and db_vs_contract differ despite exact reducer/db overlap: reducer={reducer_full_micro}, db={db_full_micro}"
            )

    failures = hard_failures + diagnostic_failures
    passed = not hard_failures
    return {
        "passed": passed,
        "hard_passed": passed,
        "hard_failures": hard_failures,
        "diagnostic_failures": diagnostic_failures,
        "failures": failures,
        "gate_reducer_db_exact": gate_reducer_db_exact,
        "gate_aligned_scoring": gate_aligned_scoring,
        "gate_parse_coverage": gate_parse_coverage,
        "gate_contract_truth_pure": gate_contract_truth_pure,
        "gate_contract_truth_resolved": gate_contract_truth_resolved,
        "gate_parser_deterministic": gate_parser_deterministic,
        "gate_no_duplicate_contract_edges": gate_no_duplicate_contract_edges,
        "gate_basket_partition": gate_basket_partition,
        "gate_basket_counts_reconciled": gate_basket_counts_reconciled,
        "gate_typescript_relative_index_contract": gate_typescript_relative_index_contract,
        "gate_class_truth_nonempty_rate": gate_class_truth_nonempty_rate,
        "gate_class_truth_match_rate": gate_class_truth_match_rate,
        "gate_scoped_call_normalization": gate_scoped_call_normalization,
        "gate_strict_contract_parity": gate_strict_contract_parity,
        "gate_limitation_scope_clean": gate_limitation_scope_clean,
        "gate_limitation_taxonomy_stable": gate_limitation_taxonomy_stable,
        "gate_strict_drop_taxonomy_stable": gate_strict_drop_taxonomy_stable,
        "gate_kind_precision_floors": gate_kind_precision_floors,
        "gate_contract_recall_min": gate_contract_recall_min,
        "gate_overreach_rate_max": gate_overreach_rate_max,
        "gate_member_call_recall_min": gate_member_call_recall_min,
        "gate_equal_contract_metrics_when_exact": gate_equal_contract_metrics,
        "reducer_db_mismatch_examples": exact_mismatches[:10],
    }
