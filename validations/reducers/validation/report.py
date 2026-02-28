# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .report_schema import validate_report_payload


def write_json(path: Path, payload: dict) -> None:
    errors = validate_report_payload(payload)
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"report payload validation failed: {joined}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_ratio(value) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _format_percent(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}%"
    return str(value)


def render_summary(payload: dict) -> List[str]:
    lines: List[str] = []
    lines.append("# SCIONA Reducer Validation Report")
    lines.append("")
    questions = payload.get("questions") or {}

    q1 = questions.get("q1") or {}
    lines.append("## Q1. Reducers vs DB Correctness")
    lines.append("")
    lines.append(f"- pass: `{q1.get('pass')}`")
    lines.append(f"- exact_required: `{q1.get('exact_required')}`")
    lines.append(
        f"- reference/candidate/intersection: `{q1.get('reference_count')}`/`{q1.get('candidate_count')}`/`{q1.get('intersection_count')}`"
    )
    lines.append(
        f"- missing/spillover: `{q1.get('missing_count')}`/`{q1.get('spillover_count')}`"
    )
    lines.append(f"- mismatch_nodes: `{q1.get('mismatch_nodes')}`")
    lines.append("")

    q2 = questions.get("q2") or {}
    lines.append("## Q2. Reducers vs Independent Within Static Contract")
    lines.append("")
    lines.append(f"- pass: `{q2.get('pass')}`")
    lines.append(
        f"- target_mutual_accuracy_min: `{_format_ratio(q2.get('target_mutual_accuracy_min'))}`"
    )
    lines.append(
        f"- target_missing_rate_max: `{_format_ratio(q2.get('target_missing_rate_max'))}`"
    )
    lines.append(
        f"- target_spillover_rate_max: `{_format_ratio(q2.get('target_spillover_rate_max'))}`"
    )
    lines.append(
        f"- scored_nodes: `{q2.get('scored_nodes')}`"
    )
    lines.append(
        f"- avg_missing_rate/avg_spillover_rate: `{_format_ratio(q2.get('avg_missing_rate'))}`/`{_format_ratio(q2.get('avg_spillover_rate'))}`"
    )
    lines.append(
        f"- avg_mutual_accuracy: `{_format_ratio(q2.get('avg_mutual_accuracy'))}`"
    )
    lines.append(
        f"- reference/candidate/intersection: `{q2.get('reference_count')}`/`{q2.get('candidate_count')}`/`{q2.get('intersection_count')}`"
    )
    lines.append(
        f"- missing/spillover: `{q2.get('missing_count')}`/`{q2.get('spillover_count')}`"
    )
    lines.append(f"- filtering_source: `{q2.get('filtering_source')}`")
    lines.append(
        f"- envelope_reference/excluded/total: `{q2.get('envelope_reference_count')}`/`{q2.get('envelope_excluded_count')}`/`{q2.get('envelope_total_count')}`"
    )
    lines.append(
        f"- contract_filtered_out_ratio: `{_format_ratio(q2.get('contract_filtered_out_ratio'))}`"
    )
    lines.append(
        f"- class_truth_unreliable_count: `{q2.get('class_truth_unreliable_count')}`"
    )
    lines.append(
        f"- class_truth_unreliable_scored_excluded_count: `{q2.get('class_truth_unreliable_scored_excluded_count')}`"
    )
    lines.append(
        f"- class_match_strategy_breakdown: `{q2.get('class_match_strategy_breakdown')}`"
    )
    lines.append(
        f"- match_provenance_breakdown: `{q2.get('match_provenance_breakdown')}`"
    )
    lines.append(
        f"- strict_contract_candidate_count_histogram: `{q2.get('strict_contract_candidate_count_histogram')}`"
    )
    lines.append(f"- by_language: `{q2.get('by_language')}`")
    lines.append("")

    q3 = questions.get("q3") or {}
    lines.append("## Q3. Beyond Static Contract Envelope")
    lines.append("")
    lines.append(
        f"- scored_nodes: `{q3.get('scored_nodes')}`"
    )
    lines.append(
        f"- avg_non_static_rate_percent: `{_format_percent(q3.get('avg_non_static_rate_percent'))}`"
    )
    percent_by_type = q3.get("by_semantic_type_non_static_avg_percent") or {}
    formatted_percent_by_type = {
        str(key): _format_percent(value) for key, value in percent_by_type.items()
    }
    lines.append(f"- avg_non_static_percent_by_type: `{formatted_percent_by_type}`")
    unresolved = q3.get("unresolved_static_defect") or {}
    lines.append(
        f"- unresolved_static_target_zero: `{unresolved.get('target_zero')}`"
    )
    lines.append(
        f"- unresolved_static_pass: `{unresolved.get('pass')}`"
    )
    lines.append(
        f"- unresolved_static_avg_percent: `{_format_percent(unresolved.get('avg_rate_percent'))}`"
    )
    lines.append("")
    return lines
