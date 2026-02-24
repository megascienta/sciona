# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .independent.shared import EdgeRecord, dedupe_edge_records, match_edge


@dataclass
class Metrics:
    in_contract_expected_edges: int
    out_of_contract_edges: int
    in_contract_precision: float | None
    in_contract_recall: float | None
    in_contract_coverage: float | None
    in_contract_false_positive_count: int
    out_of_contract_missing_count: int
    tp: int
    fp: int
    fn: int


def _safe_ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return num / den


def compute_metrics(
    expected_in_contract: List[EdgeRecord],
    out_of_contract: List[EdgeRecord],
    sciona_edges: List[EdgeRecord],
) -> Metrics:
    expected_in_contract = dedupe_edge_records(expected_in_contract)
    out_of_contract = dedupe_edge_records(out_of_contract)
    sciona_edges = dedupe_edge_records(sciona_edges)

    tp = 0
    fp = 0
    fn = 0

    unmatched_expected = expected_in_contract[:]

    for sciona_edge in sciona_edges:
        matched = False
        for idx, expected in enumerate(unmatched_expected):
            if sciona_edge.caller != expected.caller:
                continue
            if match_edge(
                sciona_edge.callee,
                sciona_edge.callee_qname,
                expected.callee,
                expected.callee_qname,
            ):
                matched = True
                tp += 1
                unmatched_expected.pop(idx)
                break
        if not matched:
            fp += 1

    fn = len(unmatched_expected)

    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    coverage = _safe_ratio(tp, len(expected_in_contract))

    out_missing = 0
    for expected in out_of_contract:
        matched = False
        for sciona_edge in sciona_edges:
            if sciona_edge.caller != expected.caller:
                continue
            if match_edge(
                sciona_edge.callee,
                sciona_edge.callee_qname,
                expected.callee,
                expected.callee_qname,
            ):
                matched = True
                break
        if not matched:
            out_missing += 1

    return Metrics(
        in_contract_expected_edges=len(expected_in_contract),
        out_of_contract_edges=len(out_of_contract),
        in_contract_precision=precision,
        in_contract_recall=recall,
        in_contract_coverage=coverage,
        in_contract_false_positive_count=fp,
        out_of_contract_missing_count=out_missing,
        tp=tp,
        fp=fp,
        fn=fn,
    )


def compare_edge_sets(
    reference_edges: List[EdgeRecord],
    candidate_edges: List[EdgeRecord],
) -> Metrics:
    return compute_metrics(reference_edges, [], candidate_edges)
