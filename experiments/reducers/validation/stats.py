# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Dict, List


def aggregate_group_metrics(rows: List[dict], metric_key: str) -> Dict[str, dict]:
    groups: Dict[str, List[dict]] = {}
    for row in rows:
        key = f"{row['language']}::{row['kind']}"
        groups.setdefault(key, []).append(row)

    metrics: Dict[str, dict] = {}
    for key, entries in groups.items():
        precision_values = [
            r[metric_key]["in_contract_precision"]
            for r in entries
            if r.get(metric_key) and r[metric_key]["in_contract_precision"] is not None
        ]
        recall_values = [
            r[metric_key]["in_contract_recall"]
            for r in entries
            if r.get(metric_key) and r[metric_key]["in_contract_recall"] is not None
        ]
        coverage_values = [
            r[metric_key]["in_contract_coverage"]
            for r in entries
            if r.get(metric_key) and r[metric_key]["in_contract_coverage"] is not None
        ]
        precision = sum(precision_values) / len(precision_values) if precision_values else None
        recall = sum(recall_values) / len(recall_values) if recall_values else None
        coverage = sum(coverage_values) / len(coverage_values) if coverage_values else None
        metrics[key] = {"precision": precision, "recall": recall, "coverage": coverage}
    return metrics


def edge_type_breakdown(rows: List[dict], metric_key: str) -> Dict[str, dict]:
    breakdown: Dict[str, dict] = {
        "calls": {"tp": 0, "fp": 0, "fn": 0},
        "imports": {"tp": 0, "fp": 0, "fn": 0},
    }
    for row in rows:
        if not row.get(metric_key):
            continue
        edge_type = "imports" if row["kind"] == "module" else "calls"
        breakdown[edge_type]["tp"] += row[metric_key]["tp"]
        breakdown[edge_type]["fp"] += row[metric_key]["fp"]
        breakdown[edge_type]["fn"] += row[metric_key]["fn"]
    return breakdown


def failure_examples(rows: List[dict], metric_key: str, limit: int = 10) -> List[dict]:
    failures = sorted(
        [r for r in rows if r.get(metric_key) and r[metric_key]["in_contract_recall"] is not None],
        key=lambda r: r[metric_key]["in_contract_recall"],
    )
    examples: List[dict] = []
    for entry in failures[:limit]:
        examples.append(
            {
                "node": entry["entity"],
                "issue": f"recall={entry[metric_key]['in_contract_recall']}",
            }
        )
    return examples


def micro(metric_rows: List[dict], metric_key: str) -> dict:
    tp = sum(row[metric_key]["tp"] for row in metric_rows if row.get(metric_key))
    fp = sum(row[metric_key]["fp"] for row in metric_rows if row.get(metric_key))
    fn = sum(row[metric_key]["fn"] for row in metric_rows if row.get(metric_key))
    precision = (tp / (tp + fp)) if (tp + fp) else None
    recall = (tp / (tp + fn)) if (tp + fn) else None
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall}
