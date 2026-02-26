# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .independent.shared import EdgeRecord, dedupe_edge_records, match_edge


@dataclass
class SetMetrics:
    reference_count: int
    candidate_count: int
    intersection_count: int
    missing_count: int
    spillover_count: int
    coverage: float | None
    spillover_ratio: float | None


def _safe_ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return num / den


def compute_set_metrics(
    reference_edges: List[EdgeRecord],
    candidate_edges: List[EdgeRecord],
) -> SetMetrics:
    reference_edges = dedupe_edge_records(reference_edges)
    candidate_edges = dedupe_edge_records(candidate_edges)

    intersection = 0
    spillover = 0

    unmatched_reference = reference_edges[:]

    for candidate in candidate_edges:
        matched = False
        for idx, reference in enumerate(unmatched_reference):
            if candidate.caller != reference.caller:
                continue
            if match_edge(
                candidate.callee,
                candidate.callee_qname,
                reference.callee,
                reference.callee_qname,
            ):
                matched = True
                intersection += 1
                unmatched_reference.pop(idx)
                break
        if not matched:
            spillover += 1

    missing = len(unmatched_reference)
    reference_count = len(reference_edges)
    candidate_count = len(candidate_edges)
    coverage = _safe_ratio(intersection, reference_count)
    spillover_ratio = _safe_ratio(spillover, reference_count)

    return SetMetrics(
        reference_count=reference_count,
        candidate_count=candidate_count,
        intersection_count=intersection,
        missing_count=missing,
        spillover_count=spillover,
        coverage=coverage,
        spillover_ratio=spillover_ratio,
    )
