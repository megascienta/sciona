# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from sciona.runtime.paths import repo_name_prefix

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

DEFAULT_SAMPLE_SIZE = 200
DEFAULT_SEED = 20260219

DEFAULT_THRESHOLDS = {
    "precision_mean_min": 0.95,
    "recall_mean_min": 0.90,
    "precision_min_by_group": 0.85,
    "recall_min_by_group": 0.80,
    "misses_out_of_contract_rate_min": 0.80,
    "reducer_db_overlap_min": 1.0,
    "reducer_filtered_overlap_min": 0.95,
    "overlap_epsilon": 1e-9,
}

LOC_BUCKETS = (
    (200, "small"),
    (800, "medium"),
    (10**9, "large"),
)

CALL_DENSITY_BUCKETS = (
    (0.05, "sparse"),
    (0.15, "moderate"),
    (10**9, "dense"),
)

DEPTH_BUCKETS = (
    (1, "top"),
    (3, "nested"),
    (10**9, "deep"),
)


@dataclass(frozen=True)
class ReportPaths:
    json_path: Path
    md_path: Path


def report_paths(repo_root: Path) -> ReportPaths:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    prefix = repo_name_prefix(repo_root)
    json_path = REPORTS_DIR / f"{prefix}_reducer_validation.json"
    md_path = REPORTS_DIR / f"{prefix}_reducer_validation.md"
    return ReportPaths(json_path=json_path, md_path=md_path)


def bucket_value(value: float, buckets: Tuple[Tuple[float, str], ...]) -> str:
    for limit, label in buckets:
        if value <= limit:
            return label
    return buckets[-1][1]
