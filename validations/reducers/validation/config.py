# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from sciona.runtime.paths import repo_name_prefix

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

DEFAULT_SAMPLE_SIZE = 200
DEFAULT_SEED = 20260219

DEFAULT_THRESHOLDS = {
    "class_truth_nonempty_rate_min": 0.95,
    "class_truth_match_rate_min": 0.95,
    "contract_recall_min": 0.95,
    "overreach_rate_max": 0.10,
    "member_call_recall_min": 0.80,
    "overlap_epsilon": 1e-9,
}

PROMPT_FITNESS_WEIGHTS = {
    "navigation": {"fp_weight": 1.0, "fn_weight": 1.0},
    "reasoning": {"fp_weight": 1.0, "fn_weight": 1.2},
}

PROMPT_RELIABILITY_VERSION = "v1"

STRICT_CONTRACT_MODE = "candidate_only_strict_contract_v1"
STRICT_CONTRACT_POLICY = {
    "mode": STRICT_CONTRACT_MODE,
    "allowed_acceptance": [
        "exact_qname",
        "module_scoped",
        "import_narrowed",
        "contract_out_of_repo_allowed",
    ],
    "allowed_drop_reasons": [
        "no_candidates",
        "unique_without_provenance",
        "ambiguous_no_caller_module",
        "ambiguous_no_in_scope_candidate",
        "ambiguous_multiple_in_scope_candidates",
    ],
}

EXPANDED_TRUTH_POLICY = {
    "scope_exclusions": ["standard_call", "external"],
    "limitation_focus": ["dynamic", "in_repo_unresolved", "relative_unresolved"],
    "confidence_tiers": {
        "high": ["in_repo_unresolved"],
        "low": ["dynamic", "relative_unresolved"],
    },
}

PROFILE_THRESHOLDS = {
    "single_language": {
        "class_truth_nonempty_rate_min": 0.95,
        "class_truth_match_rate_min": 0.95,
        "contract_recall_min": 0.95,
        "overreach_rate_max": 0.10,
        "member_call_recall_min": 0.80,
        "overlap_epsilon": 1e-9,
    },
    "multi_language": {
        "class_truth_nonempty_rate_min": 0.93,
        "class_truth_match_rate_min": 0.93,
        "contract_recall_min": 0.92,
        "overreach_rate_max": 0.13,
        "member_call_recall_min": 0.72,
        "overlap_epsilon": 1e-9,
    },
}

KIND_PRECISION_FLOORS = {
    "function": 0.75,
    "method": 0.60,
}

CALIBRATION_OVERRIDES_PATH = Path(__file__).resolve().parent / "calibration_overrides.json"


def _load_repo_kind_precision_overrides(
    path: Path = CALIBRATION_OVERRIDES_PATH,
) -> tuple[dict[str, dict[str, float]], list[dict]]:
    if not path.is_file():
        return {}, []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("overrides") or []
    loaded: dict[str, dict[str, float]] = {}
    metadata: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        repo = str(row.get("repo") or "").strip()
        kind = str(row.get("kind") or "").strip()
        try:
            minimum = float(row.get("min_precision"))
        except Exception:
            continue
        if not repo or not kind:
            continue
        loaded.setdefault(repo, {})[kind] = minimum
        metadata.append(
            {
                "repo": repo,
                "kind": kind,
                "min_precision": minimum,
                "expires_on": row.get("expires_on"),
                "reason": row.get("reason"),
            }
        )
    return loaded, metadata


def stale_repo_override_warnings(
    *,
    today: date | None = None,
    metadata: list[dict] | None = None,
) -> list[str]:
    if today is None:
        today = date.today()
    rows = metadata if metadata is not None else REPO_KIND_PRECISION_OVERRIDES_METADATA
    warnings: list[str] = []
    for row in rows:
        expires_raw = str(row.get("expires_on") or "").strip()
        if not expires_raw:
            continue
        try:
            expires_on = date.fromisoformat(expires_raw)
        except ValueError:
            warnings.append(
                f"invalid precision override expiry date for {row.get('repo')}::{row.get('kind')}: {expires_raw}"
            )
            continue
        if expires_on < today:
            warnings.append(
                f"precision override expired for {row.get('repo')}::{row.get('kind')} on {expires_on.isoformat()}"
            )
    return warnings


REPO_KIND_PRECISION_OVERRIDES, REPO_KIND_PRECISION_OVERRIDES_METADATA = (
    _load_repo_kind_precision_overrides()
)

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
