# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Dict

REPORT_SCHEMA_VERSION = "2026-02-23"

SECTION_INTERNAL_INTEGRITY = "internal_integrity"
SECTION_STATIC_CONTRACT_ALIGNMENT = "static_contract_alignment"
SECTION_ENRICHMENT_PRACTICAL = "enrichment_practical"

METRIC_DEFINITIONS: Dict[str, dict] = {
    "static_projection_precision": {
        "layer": SECTION_INTERNAL_INTEGRITY,
        "source": "reducer_vs_db",
        "formula": "tp / (tp + fp)",
    },
    "static_projection_recall": {
        "layer": SECTION_INTERNAL_INTEGRITY,
        "source": "reducer_vs_db",
        "formula": "tp / (tp + fn)",
    },
    "static_contract_precision": {
        "layer": SECTION_STATIC_CONTRACT_ALIGNMENT,
        "source": "reducer_vs_contract_truth",
        "formula": "tp / (tp + fp)",
    },
    "static_contract_recall": {
        "layer": SECTION_STATIC_CONTRACT_ALIGNMENT,
        "source": "reducer_vs_contract_truth",
        "formula": "tp / (tp + fn)",
    },
    "static_overreach_rate": {
        "layer": SECTION_STATIC_CONTRACT_ALIGNMENT,
        "source": "reducer_vs_contract_truth",
        "formula": "fp / (tp + fp)",
    },
}


def safe_ratio(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return num / den


def overreach_rate(micro_metrics: dict) -> float | None:
    tp = int(micro_metrics.get("tp") or 0)
    fp = int(micro_metrics.get("fp") or 0)
    return safe_ratio(fp, tp + fp)


def divergence_index(micro_metrics: dict) -> float | None:
    tp = int(micro_metrics.get("tp") or 0)
    fp = int(micro_metrics.get("fp") or 0)
    fn = int(micro_metrics.get("fn") or 0)
    return safe_ratio(fp + fn, tp + fp + fn)


def weighted_quality(
    *,
    tp: int,
    fp: int,
    fn: int,
    fp_weight: float,
    fn_weight: float,
) -> float | None:
    denominator = tp + (fp_weight * fp) + (fn_weight * fn)
    if denominator <= 0:
        return None
    return tp / denominator
