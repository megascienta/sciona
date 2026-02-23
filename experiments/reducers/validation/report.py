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
    lines.append(
        "- interpretation_note: independent truth is a deterministic static proxy, not absolute ground truth."
    )
    lines.append("")

    lines.append("## Run Verdict")
    lines.append("")
    invariants = payload.get("invariants", {})
    if invariants:
        lines.append(f"- passed: `{invariants.get('passed')}`")
        lines.append(f"- hard_passed: `{invariants.get('hard_passed')}`")
        quality = payload.get("quality_gates") or {}
        if quality.get("threshold_profile"):
            lines.append(f"- threshold_profile: `{quality.get('threshold_profile')}`")
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

    lines.append("## Contract Alignment (Strict Proxy)")
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
        strict_ci = static_alignment.get("uncertainty_intervals") or {}
        if strict_ci:
            lines.append(f"- uncertainty_intervals: `{strict_ci}`")
    lines.append("")

    lines.append("## Expanded Proxy Alignment (Diagnostic)")
    lines.append("")
    expanded = payload.get("enriched_truth_alignment") or {}
    if not expanded:
        lines.append("- none")
    else:
        for key in (
            "reducer_vs_enriched_truth_precision",
            "reducer_vs_enriched_truth_recall",
            "db_vs_enriched_truth_precision",
            "db_vs_enriched_truth_recall",
            "reducer_vs_enriched_truth_divergence_index",
        ):
            lines.append(f"- {key}: `{_format_value(expanded.get(key))}`")
        policy = expanded.get("inclusion_policy") or {}
        if policy:
            lines.append(f"- inclusion_policy: `{policy}`")
        tiers = expanded.get("tiers") or {}
        if tiers:
            for tier_name in ("high_conf", "full"):
                tier = tiers.get(tier_name) or {}
                lines.append(
                    f"- tier.{tier_name}: reducer_p/r=`{_format_value(tier.get('reducer_precision'))}`/`{_format_value(tier.get('reducer_recall'))}`, db_p/r=`{_format_value(tier.get('db_precision'))}`/`{_format_value(tier.get('db_recall'))}`, divergence=`{_format_value(tier.get('divergence_index'))}`"
                )
        tier_counts = expanded.get("tier_edge_counts") or {}
        if tier_counts:
            lines.append(f"- tier_edge_counts: `{tier_counts}`")
        scope_split = expanded.get("scope_split_counts") or {}
        if scope_split:
            lines.append(f"- scope_split_counts: `{scope_split}`")
        reason_breakdown = expanded.get("reason_breakdown") or {}
        if reason_breakdown:
            lines.append("Reason-level expanded proxy recall:")
            reducer_reason = reason_breakdown.get("reducer") or {}
            db_reason = reason_breakdown.get("db") or {}
            for reason in sorted(set(reducer_reason.keys()) | set(db_reason.keys())):
                rr = reducer_reason.get(reason) or {}
                dr = db_reason.get(reason) or {}
                lines.append(
                    f"- reason.{reason}: reducer_recall=`{_format_value(rr.get('recall'))}`, db_recall=`{_format_value(dr.get('recall'))}`, reducer_tp/fn=`{rr.get('tp',0)}/{rr.get('fn',0)}`"
                )
        expanded_ci = expanded.get("uncertainty_intervals") or {}
        if expanded_ci:
            lines.append(f"- uncertainty_intervals: `{expanded_ci}`")
    lines.append("")

    lines.append("## Prompt Reliability (Heuristic Diagnostics)")
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
        version = practical.get("prompt_reliability_version")
        if version:
            lines.append(f"- prompt_reliability_version: `{version}`")
        weights = practical.get("weights") or {}
        if weights:
            lines.append(f"- weights: `{weights}`")
        components = practical.get("component_contributions") or {}
        if components:
            lines.append(f"- component_contributions: `{components}`")
        noise = practical.get("noise_signal") or {}
        if noise:
            lines.append(
                f"- enrichment_noise_ratio: `{_format_value(noise.get('enrichment_noise_ratio'))}`"
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
    by_language_enriched = all_by_language.get("reducer_vs_expanded_full") or (
        all_by_language.get("reducer_vs_enriched_truth") or {}
    )
    by_language_kind = all_by_language_kind.get("reducer_vs_contract_truth") or {}
    by_language_kind_enriched = all_by_language_kind.get("reducer_vs_expanded_full") or (
        all_by_language_kind.get("reducer_vs_enriched_truth") or {}
    )
    languages = sorted(
        set(pop_by_language.keys())
        | set(sampled_by_language.keys())
        | set(by_language_projection.keys())
        | set(by_language_contract.keys())
        | set(by_language_enriched.keys())
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
            enriched = by_language_enriched.get(language) or {}
            lines.append(
                f"- {language}: sampled_nodes=`{sampled_by_language.get(language, 0)}`, population_nodes=`{pop_by_language.get(language, 0)}`, projection_p/r=`{_format_value(projection.get('precision'))}`/`{_format_value(projection.get('recall'))}`, contract_p/r=`{_format_value(contract.get('precision'))}`/`{_format_value(contract.get('recall'))}`, expanded_p/r=`{_format_value(enriched.get('precision'))}`/`{_format_value(enriched.get('recall'))}`, contract_overreach=`{_format_value(c_overreach)}`, projection_tp/fp/fn=`{p_tp}/{p_fp}/{p_fn}`, contract_tp/fp/fn=`{c_tp}/{c_fp}/{c_fn}`"
            )
            for kind in ("module", "class", "function", "method"):
                k = ((by_language_kind.get(language) or {}).get(kind) or {})
                if not k:
                    continue
                lines.append(
                    f"- {language}:{kind}: recall=`{_format_value(k.get('recall'))}`, precision=`{_format_value(k.get('precision'))}`, tp/fp/fn=`{k.get('tp', 0)}/{k.get('fp', 0)}/{k.get('fn', 0)}`"
                )
    lines.append("")
    lines.append("Expanded Proxy Alignment by language:kind")
    if not languages:
        lines.append("- none")
    else:
        for language in languages:
            for kind in ("module", "class", "function", "method"):
                strict_kind = ((by_language_kind.get(language) or {}).get(kind) or {})
                expanded_kind = ((by_language_kind_enriched.get(language) or {}).get(kind) or {})
                if not strict_kind and not expanded_kind:
                    continue
                lines.append(
                    f"- {language}:{kind}: strict_p/r=`{_format_value(strict_kind.get('precision'))}`/`{_format_value(strict_kind.get('recall'))}`, expanded_p/r=`{_format_value(expanded_kind.get('precision'))}`/`{_format_value(expanded_kind.get('recall'))}`"
                )
    lines.append("")
    lines.append("Strict vs Expanded delta by kind (top-5 worst recall delta)")
    delta_rows: list[tuple[float, str, str, float | None, float | None]] = []
    for language in languages:
        for kind in ("module", "class", "function", "method"):
            strict_kind = ((by_language_kind.get(language) or {}).get(kind) or {})
            expanded_kind = ((by_language_kind_enriched.get(language) or {}).get(kind) or {})
            strict_r = strict_kind.get("recall")
            expanded_r = expanded_kind.get("recall")
            strict_p = strict_kind.get("precision")
            expanded_p = expanded_kind.get("precision")
            if strict_r is None or expanded_r is None:
                continue
            delta = float(strict_r) - float(expanded_r)
            delta_rows.append((delta, language, kind, strict_p, expanded_p))
    if not delta_rows:
        lines.append("- none")
    else:
        for delta, language, kind, strict_p, expanded_p in sorted(delta_rows, reverse=True)[:5]:
            lines.append(
                f"- {language}:{kind}: delta_recall=`{_format_value(delta)}`, delta_precision=`{_format_value((strict_p - expanded_p) if (strict_p is not None and expanded_p is not None) else None)}`"
            )
    lines.append("")

    lines.append("## Call Resolution Diagnostics")
    lines.append("")
    call_form = (payload.get("call_form_recall") or {}).get("reducer_vs_contract_truth") or {}
    resolution_diag = (payload.get("call_resolution_diagnostics") or {}).get(
        "repo_totals"
    ) or {}
    attribution = payload.get("mismatch_attribution_breakdown") or {}
    if not call_form and not attribution and not resolution_diag:
        lines.append("- none")
    else:
        if call_form:
            for form in ("direct", "member"):
                bucket = call_form.get(form) or {}
                lines.append(
                    f"- call_form.{form}: tp=`{bucket.get('tp')}`, fn=`{bucket.get('fn')}`, recall=`{_format_value(bucket.get('recall'))}`"
                )
        if attribution:
            for key in (
                "core_missed_resolution",
                "core_overresolution",
                "normalization_contract_mismatch",
                "independent_overprojection",
            ):
                lines.append(f"- mismatch_attribution.{key}: `{attribution.get(key, 0)}`")
        if resolution_diag:
            for key in (
                "accepted_by_provenance",
                "dropped_by_reason",
                "candidate_count_histogram",
                "record_drops",
            ):
                lines.append(f"- resolution.{key}: `{resolution_diag.get(key) or {}}`")
            lang_kind = (payload.get("call_resolution_diagnostics") or {}).get(
                "by_language_and_kind"
            ) or {}
            for language in sorted(lang_kind.keys()):
                for kind in ("module", "class", "function", "method"):
                    block = (lang_kind.get(language) or {}).get(kind) or {}
                    if not block:
                        continue
                    accepted = block.get("accepted_by_provenance") or {}
                    dropped = block.get("dropped_by_reason") or {}
                    if not accepted and not dropped:
                        continue
                    lines.append(
                        f"- resolution.{language}:{kind}: accepted=`{accepted}`, dropped=`{dropped}`"
                    )
    lines.append("")

    lines.append("## Class Mapping Reliability")
    lines.append("")
    class_quality = payload.get("class_truth_mapping_quality") or {}
    if not class_quality:
        lines.append("- none")
    else:
        lines.append(
            f"- class_rows_parse_ok_with_methods: `{class_quality.get('class_rows_parse_ok_with_methods')}`"
        )
        lines.append(
            f"- class_rows_unreliable_mapping: `{class_quality.get('class_rows_unreliable_mapping')}`"
        )
        lines.append(f"- class_rows_scored: `{class_quality.get('class_rows_scored')}`")
        lines.append(
            f"- unreliable_mapping_rate: `{_format_value(class_quality.get('unreliable_mapping_rate'))}`"
        )
    lines.append("")

    lines.append("## Out-of-Contract Distribution")
    lines.append("")
    breakdown = payload.get("out_of_contract_breakdown", {}) or {}
    if not breakdown:
        lines.append("- none")
    else:
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
    lines.append("")

    lines.append("## Independent Parser Coverage & Totals")
    lines.append("")
    coverage = payload.get("independent_coverage_by_language") or {}
    if coverage:
        for language in sorted(coverage.keys()):
            info = coverage.get(language) or {}
            total = int(info.get("files_total") or 0)
            parsed = int(info.get("files_parsed") or 0)
            ratio = (parsed / total) if total else None
            lines.append(
                f"- coverage.{language}: files_parsed/files_total=`{parsed}/{total}` ({_format_value(ratio)})"
            )
    independent_totals = payload.get("independent_totals", {})
    for key in [
        "raw_call_edges",
        "raw_import_edges",
        "normalized_call_edges",
        "normalized_import_edges",
        "contract_truth_edges",
        "enrichment_edges",
        "enriched_truth_edges",
        "expanded_high_conf_edges",
        "expanded_full_edges",
        "excluded_out_of_scope_edges",
        "included_limitation_edges",
    ]:
        if key in independent_totals:
            lines.append(f"- {key}: `{independent_totals[key]}`")
    lines.append("")

    lines.append("## Core Metrics")
    lines.append("")
    if not core:
        lines.append("- none")
    else:
        for key, value in core.items():
            lines.append(f"- {key}: `{_format_value(value)}`")
    lines.append("")

    lines.append("## Action Priority Board")
    lines.append("")
    board = payload.get("action_priority_board") or []
    if not board:
        lines.append("- none")
    else:
        for item in board:
            lines.append(
                f"- [{item.get('priority')}] {item.get('area')}::{item.get('issue')} evidence=`{item.get('evidence')}`"
            )
    lines.append("")

    lines.append("## Metric Definitions & Schema")
    lines.append("")
    lines.append(f"- report_schema_version: `{payload.get('report_schema_version')}`")
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

    return lines
