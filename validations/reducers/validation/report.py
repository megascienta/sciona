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


def _summary_key(item: str) -> str | None:
    if "=" not in item:
        return None
    return item.split("=", 1)[0].strip()


def _format_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_summary(payload: dict) -> List[str]:
    lines: List[str] = []
    lines.append("# SCIONA Reducer Validation Report")
    lines.append("")

    invariants = payload.get("invariants", {}) or {}
    quality = payload.get("quality_gates", {}) or {}
    strict = payload.get("static_contract_alignment", {}) or {}
    expanded = payload.get("enriched_truth_alignment", {}) or {}
    boundary = payload.get("contract_boundary", {}) or {}
    parity = (payload.get("parity_attribution") or {}).get("repo_totals") or {}
    strict_diag = payload.get("strict_contract_diagnostics") or {}
    board = payload.get("action_priority_board") or []

    lines.append("## Run Verdict")
    lines.append("")
    lines.append(f"- hard_passed: `{invariants.get('hard_passed')}`")
    lines.append(f"- threshold_profile: `{quality.get('threshold_profile')}`")
    lines.append(
        f"- strict_precision/recall/overreach: `{_format_value(strict.get('static_contract_precision'))}`/`{_format_value(strict.get('static_contract_recall'))}`/`{_format_value(strict.get('static_overreach_rate'))}`"
    )
    full = (expanded.get("tiers") or {}).get("full") or {}
    lines.append(
        f"- expanded_full_precision/recall: `{_format_value(full.get('reducer_precision'))}`/`{_format_value(full.get('reducer_recall'))}`"
    )
    hard_failures = invariants.get("hard_failures") or []
    diagnostic_failures = invariants.get("diagnostic_failures") or []
    lines.append(f"- hard_failures: `{len(hard_failures)}`")
    lines.append(f"- diagnostic_failures: `{len(diagnostic_failures)}`")
    if hard_failures:
        for item in hard_failures[:5]:
            lines.append(f"- hard_failure: {item}")
    if diagnostic_failures:
        for item in diagnostic_failures[:5]:
            lines.append(f"- diagnostic_failure: {item}")
    lines.append("")

    lines.append("## Mismatch Source")
    lines.append("")
    ind = parity.get("independent_candidate_set") or {}
    core_sel = parity.get("core_selector") or {}
    final = parity.get("final_edge_parity") or {}
    cause = parity.get("row_dominant_cause") or {}
    if parity:
        lines.append(f"- independent_candidate_pressure: `{ind.get('candidate_pressure')}`")
        lines.append(f"- core_selector_pressure: `{core_sel.get('selector_pressure')}`")
        lines.append(f"- final_edge_parity: `{final}`")
        lines.append(f"- row_dominant_cause: `{cause}`")
    dropped = strict_diag.get("dropped_by_reason") or {}
    if dropped:
        top_dropped = sorted(dropped.items(), key=lambda item: int(item[1]), reverse=True)[:5]
        lines.append(f"- top_strict_dropped_reasons: `{dict(top_dropped)}`")
    lines.append("")

    lines.append("## Contract Boundary")
    lines.append("")
    counts = boundary.get("limitation_edge_counts") or {}
    leakage = boundary.get("contract_leakage_rate") or {}
    if counts:
        for key in (
            "independent_static_limitation_edges",
            "contract_exclusion_edges",
            "included_limitation_edges",
            "excluded_out_of_scope_edges",
        ):
            lines.append(f"- {key}: `{counts.get(key)}`")
    if leakage:
        lines.append(f"- contract_leakage_rate: `{_format_value(leakage.get('overall'))}`")
        reason_rates = leakage.get("by_reason") or {}
        if reason_rates:
            lines.append(f"- leakage_by_reason: `{reason_rates}`")
    lines.append("")

    lines.append("## Top Risks")
    lines.append("")
    high_medium = [item for item in board if item.get("priority") in {"high", "medium"}]
    if not high_medium:
        lines.append("- none")
    else:
        for item in high_medium[:5]:
            lines.append(
                f"- [{item.get('priority')}] {item.get('area')}::{item.get('issue')} evidence=`{item.get('evidence')}`"
            )
    lines.append("")

    lines.append("## Appendix")
    lines.append("")
    lines.append(f"- report_schema_version: `{payload.get('report_schema_version')}`")
    call_form = (payload.get("call_form_recall") or {}).get("reducer_vs_contract_truth") or {}
    if call_form:
        for form in ("direct", "member"):
            bucket = call_form.get(form) or {}
            lines.append(
                f"- call_form.{form}: tp=`{bucket.get('tp')}`, fn=`{bucket.get('fn')}`, recall=`{_format_value(bucket.get('recall'))}`"
            )
    lines.append("")
    return lines
