# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import List, Tuple

from .independent.shared import match_edge


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
    filter_subset_ok = True
    filter_resolved_ok = True
    no_duplicate_contract_edges = True
    for row in rows:
        filtered_edges = row.get("expected_filtered_edges") or []
        full_edges = row.get("full_truth_edges") or []
        if len(edge_full_set(filtered_edges)) != len(filtered_edges):
            no_duplicate_contract_edges = False
            break
        if len(edge_full_set(full_edges)) != len(full_edges):
            no_duplicate_contract_edges = False
            break
        for filtered_edge in filtered_edges:
            matched = False
            for full_edge in full_edges:
                if filtered_edge.get("caller") != full_edge.get("caller"):
                    continue
                if match_edge(
                    full_edge.get("callee"),
                    full_edge.get("callee_qname"),
                    filtered_edge.get("callee"),
                    filtered_edge.get("callee_qname"),
                ):
                    matched = True
                    break
            if not matched:
                filter_subset_ok = False
                break
        if not filter_subset_ok:
            break
        for edge in filtered_edges:
            if not edge.get("callee_qname"):
                filter_resolved_ok = False
                break
        if not filter_resolved_ok:
            break
    return filter_subset_ok, filter_resolved_ok, no_duplicate_contract_edges


def evaluate_invariants(
    rows: List[dict],
    *,
    reducer_full_entities: set[str],
    db_full_entities: set[str],
    reducer_full_micro: dict,
    db_full_micro: dict,
    parse_ok_files: int,
    total_files: int,
    filter_subset_ok: bool,
    filter_resolved_ok: bool,
    parser_deterministic: bool,
    no_duplicate_contract_edges: bool,
) -> dict:
    failures: List[str] = []
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
        failures.append(f"reducer/db exact mismatch on {len(exact_mismatches)} nodes")

    gate_aligned_scoring = reducer_full_entities == db_full_entities
    if not gate_aligned_scoring:
        only_reducer = sorted(reducer_full_entities - db_full_entities)[:10]
        only_db = sorted(db_full_entities - reducer_full_entities)[:10]
        failures.append(
            f"full scoring set misaligned: reducer_only={only_reducer}, db_only={only_db}"
        )

    gate_parse_coverage = (parse_ok_files == total_files)
    if not gate_parse_coverage:
        failures.append(f"independent parser parse coverage is {parse_ok_files}/{total_files}, expected full coverage")

    gate_filter_subset = filter_subset_ok
    if not gate_filter_subset:
        failures.append("filtered truth is not a subset of full truth")
    gate_filter_resolved = filter_resolved_ok
    if not gate_filter_resolved:
        failures.append("filtered truth contains unresolved targets")
    gate_parser_deterministic = parser_deterministic
    if not gate_parser_deterministic:
        failures.append("independent parser output is non-deterministic across repeated runs")
    gate_no_duplicate_contract_edges = no_duplicate_contract_edges
    if not gate_no_duplicate_contract_edges:
        failures.append("duplicate edges detected in filtered or full independent truth")

    gate_equal_full_metrics = True
    if gate_reducer_db_exact and gate_aligned_scoring:
        for key in ("tp", "fp", "fn"):
            if reducer_full_micro.get(key) != db_full_micro.get(key):
                gate_equal_full_metrics = False
                break
        if not gate_equal_full_metrics:
            failures.append(
                f"reducer_vs_full and db_vs_full differ despite exact reducer/db overlap: reducer={reducer_full_micro}, db={db_full_micro}"
            )

    passed = not failures
    return {
        "passed": passed,
        "failures": failures,
        "gate_reducer_db_exact": gate_reducer_db_exact,
        "gate_aligned_scoring": gate_aligned_scoring,
        "gate_parse_coverage": gate_parse_coverage,
        "gate_filter_subset": gate_filter_subset,
        "gate_filter_resolved": gate_filter_resolved,
        "gate_parser_deterministic": gate_parser_deterministic,
        "gate_no_duplicate_contract_edges": gate_no_duplicate_contract_edges,
        "gate_equal_full_metrics_when_exact": gate_equal_full_metrics,
        "reducer_db_mismatch_examples": exact_mismatches[:10],
    }
