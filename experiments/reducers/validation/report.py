# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path
from typing import List


def write_json(path: Path, payload: dict) -> None:
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
    lines.append("## Executive Summary")
    lines.append("")
    core = payload.get("core_metrics", {}) or {}
    duplicated_summary_keys = {
        key
        for key in ("static_contract_recall", "static_overreach_rate")
        if key in core
    }
    for item in payload.get("summary", []):
        key = _summary_key(item)
        if key and key in duplicated_summary_keys:
            continue
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Schema")
    lines.append("")
    lines.append(f"- report_schema_version: `{payload.get('report_schema_version')}`")
    lines.append("")

    lines.append("## Hard Invariants")
    lines.append("")
    invariants = payload.get("invariants", {})
    if invariants:
        lines.append(f"- passed: `{invariants.get('passed')}`")
        lines.append(f"- hard_passed: `{invariants.get('hard_passed')}`")
        for key in [
            "gate_reducer_db_exact",
            "gate_aligned_scoring",
            "gate_parse_coverage",
            "gate_contract_truth_pure",
            "gate_contract_truth_resolved",
            "gate_parser_deterministic",
            "gate_no_duplicate_contract_edges",
            "gate_typescript_relative_index_contract",
            "gate_class_truth_nonempty_rate",
            "gate_class_truth_match_rate",
            "gate_scoped_call_normalization",
            "gate_contract_recall_min",
            "gate_overreach_rate_max",
            "gate_member_call_recall_min",
            "gate_equal_contract_metrics_when_exact",
        ]:
            lines.append(f"- {key}: `{invariants.get(key)}`")
        hard_failures = invariants.get("hard_failures") or []
        diagnostic_failures = invariants.get("diagnostic_failures") or []
        for item in hard_failures:
            lines.append(f"- hard_failure: {item}")
        for item in diagnostic_failures:
            lines.append(f"- diagnostic_failure: {item}")
        if not hard_failures and not diagnostic_failures:
            for item in invariants.get("failures") or []:
                lines.append(f"- failure: {item}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Internal Integrity (Hard Gates)")
    lines.append("")
    internal = payload.get("internal_integrity") or {}
    if not internal:
        lines.append("- none")
    else:
        lines.append(f"- valid: `{internal.get('valid')}`")
        projection = internal.get("projection") or {}
        for key in (
            "static_projection_precision",
            "static_projection_recall",
        ):
            lines.append(f"- {key}: `{_format_value(projection.get(key))}`")
        det = internal.get("determinism") or {}
        lines.append(
            f"- parser_stability_score: `{_format_value(det.get('parser_stability_score'))}`"
        )
    lines.append("")

    lines.append("## Static Contract Alignment")
    lines.append("")
    static_alignment = payload.get("static_contract_alignment") or {}
    if not static_alignment:
        lines.append("- none")
    else:
        for key in (
            "static_contract_precision",
            "static_contract_recall",
            "static_overreach_rate",
            "static_divergence_index",
        ):
            lines.append(f"- {key}: `{_format_value(static_alignment.get(key))}`")
    lines.append("")

    lines.append("## Enrichment Practical (Diagnostics)")
    lines.append("")
    practical = payload.get("enrichment_practical") or {}
    if not practical:
        lines.append("- none")
    else:
        for key in (
            "navigation_structural_reliability",
            "reasoning_structural_reliability",
            "coupling_stability_index",
        ):
            lines.append(f"- {key}: `{_format_value(practical.get(key))}`")
        weights = practical.get("weights") or {}
        if weights:
            lines.append(f"- weights: `{weights}`")
        noise = practical.get("noise_signal") or {}
        if noise:
            lines.append(
                f"- enrichment_noise_ratio: `{_format_value(noise.get('enrichment_noise_ratio'))}`"
            )
    lines.append("")

    lines.append("## Core Metrics")
    lines.append("")
    if not core:
        lines.append("- none")
    else:
        for key, value in core.items():
            lines.append(f"- {key}: `{_format_value(value)}`")
    lines.append("")

    lines.append("## Metric Definitions")
    lines.append("")
    metric_defs = payload.get("metric_definitions") or {}
    if not metric_defs:
        lines.append("- none")
    else:
        for name in sorted(metric_defs.keys()):
            meta = metric_defs.get(name) or {}
            lines.append(
                f"- {name}: layer=`{meta.get('layer')}`, source=`{meta.get('source')}`, formula=`{meta.get('formula')}`"
            )
    lines.append("")

    lines.append("## Determinism")
    lines.append("")
    lines.append(f"- stability_score: `{_format_value(payload.get('stability_score'))}`")
    hashes = payload.get("stability_hashes") or []
    if hashes:
        lines.append(f"- stability_hashes: `{hashes}`")
    if payload.get("stability_error"):
        lines.append(f"- stability_error: `{payload.get('stability_error')}`")
    lines.append("")

    lines.append("## Call Form Recall")
    lines.append("")
    call_form = (payload.get("call_form_recall") or {}).get("reducer_vs_contract_truth") or {}
    if not call_form:
        lines.append("- none")
    else:
        for form in ("direct", "member"):
            bucket = call_form.get(form) or {}
            lines.append(
                f"- {form}: tp=`{bucket.get('tp')}`, fn=`{bucket.get('fn')}`, recall=`{_format_value(bucket.get('recall'))}`"
            )
    lines.append("")

    lines.append("## Language Breakdown")
    lines.append("")
    sampled_by_language: dict[str, int] = {}
    for row in payload.get("per_node", []) or []:
        language = row.get("language") or "unknown"
        sampled_by_language[language] = sampled_by_language.get(language, 0) + 1
    pop_by_language = payload.get("population_by_language") or {}
    all_by_language = payload.get("micro_metrics_by_language") or {}
    all_by_language_kind = payload.get("micro_metrics_by_language_and_kind") or {}
    by_language_projection = all_by_language.get("reducer_vs_db") or {}
    by_language_contract = all_by_language.get("reducer_vs_contract_truth") or {}
    by_language_kind = all_by_language_kind.get("reducer_vs_contract_truth") or {}
    languages = sorted(
        set(pop_by_language.keys())
        | set(sampled_by_language.keys())
        | set(by_language_projection.keys())
        | set(by_language_contract.keys())
    )
    if not languages:
        lines.append("- none")
    else:
        for language in languages:
            projection = by_language_projection.get(language) or {}
            p_tp = projection.get("tp", 0) or 0
            p_fp = projection.get("fp", 0) or 0
            p_fn = projection.get("fn", 0) or 0
            contract = by_language_contract.get(language) or {}
            c_tp = contract.get("tp", 0) or 0
            c_fp = contract.get("fp", 0) or 0
            c_fn = contract.get("fn", 0) or 0
            c_overreach = (c_fp / (c_tp + c_fp)) if (c_tp + c_fp) else None
            lines.append(
                f"- {language}: sampled_nodes=`{sampled_by_language.get(language, 0)}`, population_nodes=`{pop_by_language.get(language, 0)}`, projection_p/r=`{_format_value(projection.get('precision'))}`/`{_format_value(projection.get('recall'))}`, contract_p/r=`{_format_value(contract.get('precision'))}`/`{_format_value(contract.get('recall'))}`, contract_overreach=`{_format_value(c_overreach)}`, projection_tp/fp/fn=`{p_tp}/{p_fp}/{p_fn}`, contract_tp/fp/fn=`{c_tp}/{c_fp}/{c_fn}`"
            )
            for kind in ("module", "class", "function", "method"):
                k = ((by_language_kind.get(language) or {}).get(kind) or {})
                if not k:
                    continue
                lines.append(
                    f"- {language}:{kind}: recall=`{_format_value(k.get('recall'))}`, precision=`{_format_value(k.get('precision'))}`, tp/fp/fn=`{k.get('tp', 0)}/{k.get('fp', 0)}/{k.get('fn', 0)}`"
                )
    lines.append("")

    lines.append("## Independent Parser Totals")
    lines.append("")
    independent_totals = payload.get("independent_totals", {})
    for key in [
        "raw_call_edges",
        "raw_import_edges",
        "normalized_call_edges",
        "normalized_import_edges",
        "contract_truth_edges",
        "enrichment_edges",
    ]:
        if key in independent_totals:
            lines.append(f"- {key}: `{independent_totals[key]}`")
    lines.append("")

    lines.append("## Mismatch Attribution")
    lines.append("")
    attribution = payload.get("mismatch_attribution_breakdown") or {}
    if not attribution:
        lines.append("- none")
    else:
        for key in (
            "core_missed_resolution",
            "core_overresolution",
            "normalization_contract_mismatch",
            "independent_overprojection",
        ):
            lines.append(f"- {key}: `{attribution.get(key, 0)}`")
    lines.append("")

    lines.append("## Out-of-Contract Distribution")
    lines.append("")
    breakdown = payload.get("out_of_contract_breakdown", {}) or {}
    if not breakdown:
        lines.append("- none")
        return lines

    by_edge_type: dict[str, int] = {}
    for key, count in breakdown.items():
        edge_type = key.split("::", 1)[0] if "::" in key else "unknown"
        by_edge_type[edge_type] = by_edge_type.get(edge_type, 0) + int(count)

    for edge_type in sorted(by_edge_type.keys()):
        lines.append(f"- {edge_type}: `{by_edge_type[edge_type]}`")
    lines.append("")
    lines.append("Breakdown by `edge_type::language::reason`:")
    for key in sorted(breakdown.keys()):
        lines.append(f"- {key}: `{breakdown[key]}`")
    lines.append("")
    lines.append(
        "Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded."
    )

    return lines
