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
    duplicated_summary_keys = {key for key in ("contract_recall", "overreach_rate") if key in core}
    for item in payload.get("summary", []):
        key = _summary_key(item)
        if key and key in duplicated_summary_keys:
            continue
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Hard Invariants")
    lines.append("")
    invariants = payload.get("invariants", {})
    if invariants:
        lines.append(f"- passed: `{invariants.get('passed')}`")
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
        for item in invariants.get("failures") or []:
            lines.append(f"- failure: {item}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Core Metrics")
    lines.append("")
    if not core:
        lines.append("- none")
    else:
        for key, value in core.items():
            lines.append(f"- {key}: `{_format_value(value)}`")
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
    by_language = (
        (payload.get("micro_metrics_by_language") or {}).get("reducer_vs_contract_truth")
        or {}
    )
    by_language_kind = (
        (payload.get("micro_metrics_by_language_and_kind") or {}).get(
            "reducer_vs_contract_truth"
        )
        or {}
    )
    languages = sorted(
        set(pop_by_language.keys()) | set(sampled_by_language.keys()) | set(by_language.keys())
    )
    if not languages:
        lines.append("- none")
    else:
        for language in languages:
            metrics = by_language.get(language) or {}
            tp = metrics.get("tp", 0) or 0
            fp = metrics.get("fp", 0) or 0
            fn = metrics.get("fn", 0) or 0
            overreach = (fp / (tp + fp)) if (tp + fp) else None
            lines.append(
                f"- {language}: sampled_nodes=`{sampled_by_language.get(language, 0)}`, population_nodes=`{pop_by_language.get(language, 0)}`, recall=`{_format_value(metrics.get('recall'))}`, overreach_rate=`{_format_value(overreach)}`, tp/fp/fn=`{tp}/{fp}/{fn}`"
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
