# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path
from statistics import mean

from sciona.pipelines.progress import make_progress_factory
from sciona.runtime import packaging as runtime_packaging
from sciona.runtime.paths import repo_name_prefix

from . import config
from .connections import open_core_db
from .db_adapter import list_nodes_from_artifacts, open_artifact_db
from .evaluation import (
    DbEdgeSource,
    ReducerEdgeSource,
    ResolverCache,
    build_normalized_edge_maps,
    evaluate_entities,
    prepare_parse_map,
    sample_entities_from_db,
)
from .evaluation_parse import parse_independent_files
from .evaluation_resolution import build_independent_call_resolution
from .report import render_summary, write_json, write_markdown
from .reducer_queries import get_snapshot_id


REPORT_SCHEMA_VERSION = "2026-02-27"
Q2_FILTERING_SOURCE = "core_only"
NON_STATIC_REASONS = {"dynamic", "decorator"}
DECORATOR_REASONS = {"decorator"}
DYNAMIC_DISPATCH_REASONS = {"dynamic"}
UNRESOLVED_STATIC_REASONS = {"in_repo_unresolved", "relative_unresolved", "unknown"}


def _aggregate_set_metrics(rows: list[dict], key: str) -> dict:
    reference_count = sum(
        int((row.get(key) or {}).get("reference_count") or 0) for row in rows if row.get(key)
    )
    candidate_count = sum(
        int((row.get(key) or {}).get("candidate_count") or 0) for row in rows if row.get(key)
    )
    intersection_count = sum(
        int((row.get(key) or {}).get("intersection_count") or 0) for row in rows if row.get(key)
    )
    missing_count = sum(
        int((row.get(key) or {}).get("missing_count") or 0) for row in rows if row.get(key)
    )
    spillover_count = sum(
        int((row.get(key) or {}).get("spillover_count") or 0) for row in rows if row.get(key)
    )
    coverage = (
        (intersection_count / reference_count) if reference_count else None
    )
    spillover_ratio = (
        (spillover_count / reference_count) if reference_count else None
    )
    match_provenance_breakdown: dict[str, int] = {}
    for row in rows:
        breakdown = (row.get(key) or {}).get("match_provenance_breakdown") or {}
        for provenance, count in breakdown.items():
            match_provenance_breakdown[str(provenance)] = (
                int(match_provenance_breakdown.get(str(provenance), 0)) + int(count or 0)
            )
    return {
        "reference_count": reference_count,
        "candidate_count": candidate_count,
        "intersection_count": intersection_count,
        "missing_count": missing_count,
        "spillover_count": spillover_count,
        "coverage": coverage,
        "spillover_ratio": spillover_ratio,
        "match_provenance_breakdown": dict(sorted(match_provenance_breakdown.items())),
    }


def _safe_ratio(numerator: float | int, denominator: float | int) -> float | None:
    if not denominator:
        return None
    return float(numerator) / float(denominator)


def _build_q2_node_rates(metrics: dict | None) -> dict | None:
    if not metrics:
        return None
    reference_count = int(metrics.get("reference_count") or 0)
    if reference_count <= 0:
        return None
    missing_count = int(metrics.get("missing_count") or 0)
    spillover_count = int(metrics.get("spillover_count") or 0)
    intersection_count = int(metrics.get("intersection_count") or 0)
    candidate_count = int(metrics.get("candidate_count") or 0)
    union_count = reference_count + candidate_count - intersection_count
    return {
        "missing_rate": _safe_ratio(missing_count, reference_count),
        "spillover_rate": _safe_ratio(spillover_count, reference_count),
        "mutual_accuracy": _safe_ratio(intersection_count, union_count),
    }


def _build_q2_hints_augmented_rates(
    *,
    metrics: dict | None,
    excluded_limitation_count: int,
) -> dict | None:
    if not metrics:
        return None
    reference_count = int(metrics.get("reference_count") or 0) + int(
        excluded_limitation_count or 0
    )
    if reference_count <= 0:
        return None
    missing_count = int(metrics.get("missing_count") or 0) + int(excluded_limitation_count or 0)
    spillover_count = int(metrics.get("spillover_count") or 0)
    intersection_count = int(metrics.get("intersection_count") or 0)
    candidate_count = int(metrics.get("candidate_count") or 0)
    union_count = reference_count + candidate_count - intersection_count
    return {
        "missing_rate": _safe_ratio(missing_count, reference_count),
        "spillover_rate": _safe_ratio(spillover_count, reference_count),
        "mutual_accuracy": _safe_ratio(intersection_count, union_count),
    }


def _passes_q2_gate(
    *,
    avg_missing_rate: float | None,
    avg_spillover_rate: float | None,
    avg_mutual_accuracy: float | None,
    target: float,
) -> bool:
    if (
        avg_missing_rate is None
        or avg_spillover_rate is None
        or avg_mutual_accuracy is None
    ):
        return False
    return bool(
        avg_missing_rate <= (1.0 - target)
        and avg_spillover_rate <= (1.0 - target)
        and avg_mutual_accuracy >= target
    )


def _build_reason_breakdown(
    records: list[dict],
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    counts_by_entity: dict[str, int] = {}
    semantic_type_counts_by_entity: dict[str, dict[str, int]] = {}
    for record in records:
        entity_qname = str(record.get("entity") or "")
        if not entity_qname:
            continue
        counts_by_entity[entity_qname] = int(counts_by_entity.get(entity_qname, 0)) + 1
        semantic_type = str(record.get("semantic_type") or "unknown")
        per_entity = semantic_type_counts_by_entity.setdefault(entity_qname, {})
        per_entity[semantic_type] = int(per_entity.get(semantic_type, 0)) + 1
    return counts_by_entity, semantic_type_counts_by_entity


def _build_per_node_rate_payload(
    *,
    rows: list[dict],
    counts_by_entity: dict[str, int],
    semantic_type_counts_by_entity: dict[str, dict[str, int]],
) -> dict:
    node_rates: list[dict] = []
    for row in rows:
        q2_metrics = row.get("set_q2_reducer_vs_independent_contract") or {}
        reference_count = int(q2_metrics.get("reference_count") or 0)
        if reference_count <= 0:
            continue
        entity_qname = str(row.get("entity") or "")
        count = int(counts_by_entity.get(entity_qname) or 0)
        rate = _safe_ratio(count, reference_count)
        node_rates.append(
            {
                "entity": entity_qname,
                "reference_count": reference_count,
                "edge_count": count,
                "rate": rate,
            }
        )

    avg_rate = (
        mean(item["rate"] for item in node_rates if item["rate"] is not None)
        if node_rates
        else None
    )
    by_semantic_type_rate: dict[str, float] = {}
    semantic_types = {
        semantic for by_type in semantic_type_counts_by_entity.values() for semantic in by_type
    }
    for semantic_type in sorted(semantic_types):
        per_node_rates: list[float] = []
        for row in rows:
            q2_metrics = row.get("set_q2_reducer_vs_independent_contract") or {}
            reference_count = int(q2_metrics.get("reference_count") or 0)
            if reference_count <= 0:
                continue
            entity_qname = str(row.get("entity") or "")
            semantic_count = int(
                (semantic_type_counts_by_entity.get(entity_qname) or {}).get(semantic_type) or 0
            )
            rate = _safe_ratio(semantic_count, reference_count)
            if rate is not None:
                per_node_rates.append(rate)
        by_semantic_type_rate[semantic_type] = mean(per_node_rates) if per_node_rates else 0.0

    return {
        "scored_nodes": len(node_rates),
        "avg_rate": avg_rate,
        "avg_rate_percent": (avg_rate * 100.0) if avg_rate is not None else None,
        "total_edges": sum(counts_by_entity.values()),
        "by_semantic_type_avg_rate": dict(sorted(by_semantic_type_rate.items())),
        "by_semantic_type_avg_percent": {
            key: value * 100.0 for key, value in sorted(by_semantic_type_rate.items())
        },
    }


def _build_report_payload(
    *,
    repo_root: Path,
    rows: list[dict],
    out_of_contract_meta: list[dict],
    sampling_metadata: dict | None = None,
) -> dict:
    scored_rows_q2 = [
        row
        for row in rows
        if row.get("set_q2_reducer_vs_independent_contract") is not None
    ]
    scored_rows_q2_syntax = [
        row
        for row in rows
        if row.get("set_q2_reducer_vs_independent_syntax") is not None
    ]
    scored_rows_q1 = [row for row in rows if row.get("set_q1_reducer_vs_db") is not None]
    q1_agg = _aggregate_set_metrics(scored_rows_q1, "set_q1_reducer_vs_db")
    q2_agg = _aggregate_set_metrics(scored_rows_q2, "set_q2_reducer_vs_independent_contract")
    q2_syntax_agg = _aggregate_set_metrics(
        scored_rows_q2_syntax, "set_q2_reducer_vs_independent_syntax"
    )
    q2_excluded_total = sum(
        int((row.get("q2_filtering_stats") or {}).get("excluded_total_count") or 0)
        for row in rows
    )
    q2_excluded_out_of_scope = sum(
        int((row.get("q2_filtering_stats") or {}).get("excluded_out_of_scope_count") or 0)
        for row in rows
    )
    q2_excluded_limitation = sum(
        int((row.get("q2_filtering_stats") or {}).get("excluded_limitation_count") or 0)
        for row in rows
    )
    q2_excluded_by_reason: dict[str, int] = {}
    for row in rows:
        stats = row.get("q2_filtering_stats") or {}
        by_reason = {}
        by_reason.update(stats.get("excluded_out_of_scope_by_reason") or {})
        by_reason.update(stats.get("excluded_limitation_by_reason") or {})
        for reason, count in by_reason.items():
            q2_excluded_by_reason[str(reason)] = (
                int(q2_excluded_by_reason.get(str(reason), 0)) + int(count or 0)
            )
    q2_reference_total = int(q2_agg.get("reference_count") or 0)
    q2_envelope_total = q2_reference_total + q2_excluded_total
    q2_contract_filtered_out_ratio = _safe_ratio(q2_excluded_total, q2_envelope_total)
    strict_contract_candidate_histogram: dict[str, int] = {}
    strict_contract_dropped_by_reason: dict[str, int] = {}
    caller_divergence_aggregate = {
        "rows_with_alt_caller_match": 0,
        "alternate_caller_match_count": 0,
        "missing_reference_edges_count": 0,
        "missing_reference_with_qname_count": 0,
    }
    for row in rows:
        diagnostics = row.get("q2_ground_truth_diagnostics") or {}
        histogram = diagnostics.get("strict_contract_candidate_count_histogram") or {}
        for bucket, count in histogram.items():
            strict_contract_candidate_histogram[str(bucket)] = (
                int(strict_contract_candidate_histogram.get(str(bucket), 0))
                + int(count or 0)
            )
        dropped = diagnostics.get("strict_contract_dropped_by_reason") or {}
        for reason, count in dropped.items():
            strict_contract_dropped_by_reason[str(reason)] = (
                int(strict_contract_dropped_by_reason.get(str(reason), 0))
                + int(count or 0)
            )
        caller_divergence = row.get("caller_divergence_diagnostics") or {}
        if bool(caller_divergence.get("has_alternate_caller_match")):
            caller_divergence_aggregate["rows_with_alt_caller_match"] += 1
        caller_divergence_aggregate["alternate_caller_match_count"] += int(
            caller_divergence.get("alternate_caller_match_count") or 0
        )
        caller_divergence_aggregate["missing_reference_edges_count"] += int(
            caller_divergence.get("missing_reference_edges_count") or 0
        )
        caller_divergence_aggregate["missing_reference_with_qname_count"] += int(
            caller_divergence.get("missing_reference_with_qname_count") or 0
        )
    class_truth_unreliable_count = 0
    class_truth_unreliable_scored_excluded_count = 0
    class_match_strategy_breakdown: dict[str, int] = {}
    for row in rows:
        if str(row.get("kind") or "") != "class":
            continue
        diagnostics = row.get("q2_ground_truth_diagnostics") or {}
        strategy = str(diagnostics.get("class_match_strategy") or "none")
        class_match_strategy_breakdown[strategy] = (
            int(class_match_strategy_breakdown.get(strategy, 0)) + 1
        )
        is_unreliable = bool(diagnostics.get("class_truth_unreliable"))
        if not is_unreliable:
            continue
        class_truth_unreliable_count += 1
        if row.get("set_q2_reducer_vs_independent_contract") is None:
            class_truth_unreliable_scored_excluded_count += 1

    q2_target = 0.99
    q2_node_rates: list[dict] = []
    for row in scored_rows_q2:
        rates = _build_q2_node_rates(row.get("set_q2_reducer_vs_independent_contract") or {})
        if rates is None:
            continue
        q2_node_rates.append(
            {
                "entity": row["entity"],
                "language": row["language"],
                "kind": row["kind"],
                "file_path": row["file_path"],
                "module_qualified_name": row["module_qualified_name"],
                **rates,
            }
        )
    avg_missing_rate = mean(item["missing_rate"] for item in q2_node_rates) if q2_node_rates else None
    avg_spillover_rate = mean(item["spillover_rate"] for item in q2_node_rates) if q2_node_rates else None
    avg_mutual_accuracy = (
        mean(item["mutual_accuracy"] for item in q2_node_rates if item["mutual_accuracy"] is not None)
        if q2_node_rates
        else None
    )
    q2_hints_node_rates: list[dict] = []
    for row in scored_rows_q2:
        rates = _build_q2_hints_augmented_rates(
            metrics=row.get("set_q2_reducer_vs_independent_contract") or {},
            excluded_limitation_count=int(
                (row.get("q2_filtering_stats") or {}).get("excluded_limitation_count") or 0
            ),
        )
        if rates is None:
            continue
        q2_hints_node_rates.append(
            {
                "entity": row["entity"],
                "language": row["language"],
                "kind": row["kind"],
                "file_path": row["file_path"],
                "module_qualified_name": row["module_qualified_name"],
                **rates,
            }
        )
    avg_missing_rate_hints = (
        mean(item["missing_rate"] for item in q2_hints_node_rates) if q2_hints_node_rates else None
    )
    avg_spillover_rate_hints = (
        mean(item["spillover_rate"] for item in q2_hints_node_rates)
        if q2_hints_node_rates
        else None
    )
    avg_mutual_accuracy_hints = (
        mean(
            item["mutual_accuracy"]
            for item in q2_hints_node_rates
            if item["mutual_accuracy"] is not None
        )
        if q2_hints_node_rates
        else None
    )
    q2_pass = _passes_q2_gate(
        avg_missing_rate=avg_missing_rate,
        avg_spillover_rate=avg_spillover_rate,
        avg_mutual_accuracy=avg_mutual_accuracy,
        target=q2_target,
    )
    q1_pass = bool(
        int(q1_agg.get("missing_count") or 0) == 0
        and int(q1_agg.get("spillover_count") or 0) == 0
    )
    q1_mismatch_nodes = sum(
        1
        for row in scored_rows_q1
        if int((row.get("set_q1_reducer_vs_db") or {}).get("missing_count") or 0) > 0
        or int((row.get("set_q1_reducer_vs_db") or {}).get("spillover_count") or 0) > 0
    )
    q2_by_language_raw: dict[str, list[dict]] = {}
    for rates in q2_node_rates:
        language = str(rates.get("language") or "unknown")
        q2_by_language_raw.setdefault(language, []).append(rates)
    q2_by_language: dict[str, dict[str, float | int | bool | None]] = {}
    for language, values in sorted(q2_by_language_raw.items()):
        lang_avg_missing = mean(item["missing_rate"] for item in values) if values else None
        lang_avg_spillover = mean(item["spillover_rate"] for item in values) if values else None
        lang_avg_mutual = (
            mean(item["mutual_accuracy"] for item in values if item["mutual_accuracy"] is not None)
            if values
            else None
        )
        q2_by_language[language] = {
            "scored_nodes": len(values),
            "avg_missing_rate": lang_avg_missing,
            "avg_spillover_rate": lang_avg_spillover,
            "avg_mutual_accuracy": lang_avg_mutual,
            "pass": _passes_q2_gate(
                avg_missing_rate=lang_avg_missing,
                avg_spillover_rate=lang_avg_spillover,
                avg_mutual_accuracy=lang_avg_mutual,
                target=q2_target,
            ),
        }
    q2_language_pass = all(
        bool(bucket.get("pass")) for bucket in q2_by_language.values()
    ) if q2_by_language else False

    non_static_records = [
        record
        for record in out_of_contract_meta
        if str(record.get("reason") or "") in NON_STATIC_REASONS
    ]
    decorator_records = [
        record
        for record in out_of_contract_meta
        if str(record.get("reason") or "") in DECORATOR_REASONS
    ]
    dynamic_dispatch_records = [
        record
        for record in out_of_contract_meta
        if str(record.get("reason") or "") in DYNAMIC_DISPATCH_REASONS
    ]
    unresolved_static_records = [
        record
        for record in out_of_contract_meta
        if str(record.get("reason") or "") in UNRESOLVED_STATIC_REASONS
    ]
    non_static_counts, non_static_semantic_counts = _build_reason_breakdown(non_static_records)
    unresolved_counts, unresolved_semantic_counts = _build_reason_breakdown(
        unresolved_static_records
    )
    decorator_counts, decorator_semantic_counts = _build_reason_breakdown(decorator_records)
    dynamic_dispatch_counts, dynamic_dispatch_semantic_counts = _build_reason_breakdown(
        dynamic_dispatch_records
    )
    non_static_metrics = _build_per_node_rate_payload(
        rows=rows,
        counts_by_entity=non_static_counts,
        semantic_type_counts_by_entity=non_static_semantic_counts,
    )
    unresolved_static_metrics = _build_per_node_rate_payload(
        rows=rows,
        counts_by_entity=unresolved_counts,
        semantic_type_counts_by_entity=unresolved_semantic_counts,
    )
    decorator_metrics = _build_per_node_rate_payload(
        rows=rows,
        counts_by_entity=decorator_counts,
        semantic_type_counts_by_entity=decorator_semantic_counts,
    )
    dynamic_dispatch_metrics = _build_per_node_rate_payload(
        rows=rows,
        counts_by_entity=dynamic_dispatch_counts,
        semantic_type_counts_by_entity=dynamic_dispatch_semantic_counts,
    )
    unresolved_static_zero = bool(
        (unresolved_static_metrics.get("avg_rate") or 0.0) == 0.0
        and int(unresolved_static_metrics.get("total_edges") or 0) == 0
    )

    invariants = {
        "passed": bool(q2_pass),
        "pipeline_self_consistent": bool(q1_pass),
        "independently_verified": bool(q2_pass),
        "hard_passed": bool(q1_pass and q2_pass),
        "q1_reducer_vs_db_exact": q1_pass,
        "q2_reducer_vs_independent_overlap_macro": q2_pass,
        "q2_per_language_near_100": q2_language_pass,
        "q3_non_static_descriptive_only": True,
        "unresolved_static_zero": unresolved_static_zero,
    }
    quality_gates = {
        "q2_target_mutual_accuracy_min": q2_target,
        "q2_target_missing_rate_max": (1.0 - q2_target),
        "q2_target_spillover_rate_max": (1.0 - q2_target),
        "q2_filtering_source": Q2_FILTERING_SOURCE,
        "unresolved_static_target_zero": True,
    }

    compact_rows: list[dict] = []
    for row in rows:
        diagnostics = row.get("q2_ground_truth_diagnostics") or {}
        mismatch_reason_bucket = dict(
            sorted((diagnostics.get("strict_contract_dropped_by_reason") or {}).items())
        )
        compact_rows.append(
            {
                "entity": row["entity"],
                "language": row["language"],
                "kind": row["kind"],
                "file_path": row["file_path"],
                "module_qualified_name": row["module_qualified_name"],
                "set_q1_reducer_vs_db": row.get("set_q1_reducer_vs_db"),
                "set_q2_reducer_vs_independent_contract": row.get(
                    "set_q2_reducer_vs_independent_contract"
                ),
                "set_q2_reducer_vs_independent_syntax": row.get(
                    "set_q2_reducer_vs_independent_syntax"
                ),
                "basket2_edges": row.get("basket2_edges"),
                "q2_filtering_stats": row.get("q2_filtering_stats"),
                "q2_ground_truth_diagnostics": row.get("q2_ground_truth_diagnostics"),
                "caller_divergence_diagnostics": row.get("caller_divergence_diagnostics"),
                "mismatch_reason_bucket": mismatch_reason_bucket,
                "q2_node_rates": _build_q2_node_rates(
                    row.get("set_q2_reducer_vs_independent_contract")
                ),
                "q3_non_static_rate_percent": (
                    (
                        _safe_ratio(
                            int(non_static_counts.get(str(row.get("entity") or "")) or 0),
                            int(
                                (row.get("set_q2_reducer_vs_independent_contract") or {}).get(
                                    "reference_count"
                                )
                                or 0
                            ),
                        )
                        or 0.0
                    )
                    * 100.0
                )
                if int((row.get("set_q2_reducer_vs_independent_contract") or {}).get("reference_count") or 0)
                > 0
                else None,
                "unresolved_static_rate_percent": (
                    (
                        _safe_ratio(
                            int(unresolved_counts.get(str(row.get("entity") or "")) or 0),
                            int(
                                (row.get("set_q2_reducer_vs_independent_contract") or {}).get(
                                    "reference_count"
                                )
                                or 0
                            ),
                        )
                        or 0.0
                    )
                    * 100.0
                )
                if int((row.get("set_q2_reducer_vs_independent_contract") or {}).get("reference_count") or 0)
                > 0
                else None,
            }
        )

    summary = [
        f"repo={repo_name_prefix(repo_root)}",
        f"sampled_nodes={len(rows)}",
        f"q1_reducer_vs_db_exact={q1_pass}",
        f"q2_reducer_vs_independent_overlap_macro={q2_pass}",
        f"q3_avg_non_static_percent={((non_static_metrics.get('avg_rate') or 0.0) * 100.0):.4f}"
        if non_static_metrics.get("avg_rate") is not None
        else "q3_avg_non_static_percent=None",
        f"unresolved_static_avg_percent={((unresolved_static_metrics.get('avg_rate') or 0.0) * 100.0):.4f}"
        if unresolved_static_metrics.get("avg_rate") is not None
        else "unresolved_static_avg_percent=None",
    ]
    mismatch_candidates: list[tuple[int, int, int, str, dict]] = []
    for row in rows:
        metrics = row.get("set_q2_reducer_vs_independent_contract") or {}
        missing_count = int(metrics.get("missing_count") or 0)
        spillover_count = int(metrics.get("spillover_count") or 0)
        reference_count = int(metrics.get("reference_count") or 0)
        total = missing_count + spillover_count
        if total <= 0:
            continue
        missing_rate = _safe_ratio(missing_count, reference_count)
        spillover_rate = _safe_ratio(spillover_count, reference_count)
        mismatch_candidates.append(
            (
                total,
                missing_count,
                spillover_count,
                str(row.get("entity") or ""),
                {
                    "entity": row.get("entity"),
                    "language": row.get("language"),
                    "kind": row.get("kind"),
                    "file_path": row.get("file_path"),
                    "module_qualified_name": row.get("module_qualified_name"),
                    "missing_count": missing_count,
                    "spillover_count": spillover_count,
                    "reference_count": reference_count,
                    "missing_rate": missing_rate,
                    "spillover_rate": spillover_rate,
                    "total_mismatch": total,
                    "mismatch_reason_bucket": dict(
                        sorted(
                            (
                                (
                                    row.get("q2_ground_truth_diagnostics")
                                    or {}
                                ).get("strict_contract_dropped_by_reason")
                                or {}
                            ).items()
                        )
                    ),
                    "caller_divergence_diagnostics": row.get("caller_divergence_diagnostics"),
                },
            )
        )
    mismatch_candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
    top_mismatch_signatures = [item[4] for item in mismatch_candidates[:20]]

    payload = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "summary": summary,
        "invariants": invariants,
        "quality_gates": quality_gates,
        "per_node": compact_rows,
        "questions": {
            "q1": {
                "title": "reducers vs DB correctness",
                "pass": q1_pass,
                "exact_required": True,
                "reference_count": q1_agg.get("reference_count"),
                "candidate_count": q1_agg.get("candidate_count"),
                "intersection_count": q1_agg.get("intersection_count"),
                "missing_count": q1_agg.get("missing_count"),
                "spillover_count": q1_agg.get("spillover_count"),
                "mismatch_nodes": q1_mismatch_nodes,
            },
            "q2": {
                "title": "reducers vs independent within static contract",
                "pass": q2_pass,
                "target_mutual_accuracy_min": q2_target,
                "target_missing_rate_max": (1.0 - q2_target),
                "target_spillover_rate_max": (1.0 - q2_target),
                "scored_nodes": len(q2_node_rates),
                "avg_missing_rate": avg_missing_rate,
                "avg_spillover_rate": avg_spillover_rate,
                "avg_mutual_accuracy": avg_mutual_accuracy,
                "reference_count": q2_agg.get("reference_count"),
                "candidate_count": q2_agg.get("candidate_count"),
                "intersection_count": q2_agg.get("intersection_count"),
                "missing_count": q2_agg.get("missing_count"),
                "spillover_count": q2_agg.get("spillover_count"),
                "by_language": q2_by_language,
                "filtering_source": Q2_FILTERING_SOURCE,
                "envelope_reference_count": q2_reference_total,
                "envelope_excluded_count": q2_excluded_total,
                "envelope_excluded_out_of_scope_count": q2_excluded_out_of_scope,
                "envelope_excluded_limitation_count": q2_excluded_limitation,
                "envelope_total_count": q2_envelope_total,
                "contract_filtered_out_ratio": q2_contract_filtered_out_ratio,
                "envelope_excluded_by_reason": dict(sorted(q2_excluded_by_reason.items())),
                "match_provenance_breakdown": q2_agg.get("match_provenance_breakdown"),
                "strict_contract_candidate_count_histogram": dict(
                    sorted(strict_contract_candidate_histogram.items())
                ),
                "strict_contract_dropped_by_reason": dict(
                    sorted(strict_contract_dropped_by_reason.items())
                ),
                "caller_divergence_summary": caller_divergence_aggregate,
                "class_truth_unreliable_count": class_truth_unreliable_count,
                "class_truth_unreliable_scored_excluded_count": (
                    class_truth_unreliable_scored_excluded_count
                ),
                "class_match_strategy_breakdown": dict(
                    sorted(class_match_strategy_breakdown.items())
                ),
                "core_contract_overlap": {
                    "reference_count": q2_reference_total,
                    "candidate_count": q2_agg.get("candidate_count"),
                    "intersection_count": q2_agg.get("intersection_count"),
                    "missing_count": q2_agg.get("missing_count"),
                    "spillover_count": q2_agg.get("spillover_count"),
                    "avg_missing_rate": avg_missing_rate,
                    "avg_spillover_rate": avg_spillover_rate,
                    "avg_mutual_accuracy": avg_mutual_accuracy,
                },
                "contract_plus_resolution_hints": {
                    "reference_count": q2_reference_total + q2_excluded_limitation,
                    "candidate_count": q2_agg.get("candidate_count"),
                    "intersection_count": q2_agg.get("intersection_count"),
                    "missing_count": int(q2_agg.get("missing_count") or 0)
                    + q2_excluded_limitation,
                    "spillover_count": q2_agg.get("spillover_count"),
                    "avg_missing_rate": avg_missing_rate_hints,
                    "avg_spillover_rate": avg_spillover_rate_hints,
                    "avg_mutual_accuracy": avg_mutual_accuracy_hints,
                },
                "top_mismatch_signatures": top_mismatch_signatures,
            },
            "q2_syntax": {
                "title": "reducers vs independent syntax-only baseline",
                "scored_nodes": len(scored_rows_q2_syntax),
                "reference_count": q2_syntax_agg.get("reference_count"),
                "candidate_count": q2_syntax_agg.get("candidate_count"),
                "intersection_count": q2_syntax_agg.get("intersection_count"),
                "missing_count": q2_syntax_agg.get("missing_count"),
                "spillover_count": q2_syntax_agg.get("spillover_count"),
                "coverage": q2_syntax_agg.get("coverage"),
                "spillover_ratio": q2_syntax_agg.get("spillover_ratio"),
                "match_provenance_breakdown": q2_syntax_agg.get("match_provenance_breakdown"),
            },
            "q3": {
                "title": "non-static edges beyond contract envelope",
                "descriptive_only": True,
                "scored_nodes": non_static_metrics.get("scored_nodes"),
                "avg_non_static_rate": non_static_metrics.get("avg_rate"),
                "avg_non_static_rate_percent": non_static_metrics.get("avg_rate_percent"),
                "decorator_rate_percent": decorator_metrics.get("avg_rate_percent"),
                "dynamic_dispatch_rate_percent": dynamic_dispatch_metrics.get(
                    "avg_rate_percent"
                ),
                "total_non_static_edges": non_static_metrics.get("total_edges"),
                "by_semantic_type_non_static_avg_rate": non_static_metrics.get(
                    "by_semantic_type_avg_rate"
                ),
                "by_semantic_type_non_static_avg_percent": non_static_metrics.get(
                    "by_semantic_type_avg_percent"
                ),
                "unresolved_static_defect": {
                    "target_zero": True,
                    "pass": unresolved_static_zero,
                    "scored_nodes": unresolved_static_metrics.get("scored_nodes"),
                    "avg_rate": unresolved_static_metrics.get("avg_rate"),
                    "avg_rate_percent": unresolved_static_metrics.get("avg_rate_percent"),
                    "total_edges": unresolved_static_metrics.get("total_edges"),
                    "by_semantic_type_avg_rate": unresolved_static_metrics.get(
                        "by_semantic_type_avg_rate"
                    ),
                    "by_semantic_type_avg_percent": unresolved_static_metrics.get(
                        "by_semantic_type_avg_percent"
                    ),
                },
            },
        },
    }
    if sampling_metadata:
        payload["sampling"] = sampling_metadata
    return payload


def run_validation(
    *,
    repo_root: Path,
    nodes: int,
    seed: int,
) -> int:
    repo_root = repo_root.resolve()
    reports = config.report_paths(repo_root)
    sampling_metadata: dict | None = None

    with open_core_db(repo_root) as conn:
        snapshot_id = get_snapshot_id(conn)
        resolver = ResolverCache(conn, snapshot_id)
        with open_artifact_db(repo_root) as artifact_conn:
            progress_factory = make_progress_factory()
            print("Loading nodes... ", end="", flush=True)
            nodes_data = list_nodes_from_artifacts(
                artifact_conn,
                conn,
                snapshot_id,
                node_kinds=["module", "class", "function", "method"],
            )
            print(f"done ({len(nodes_data)} nodes)")

            module_entries = [
                entry
                for entry in nodes_data
                if (entry.get("node_type") or entry.get("node_kind")) == "module"
                and entry.get("file_path")
                and entry.get("qualified_name")
            ]
            full_module_names = {
                entry.get("qualified_name")
                for entry in nodes_data
                if (entry.get("node_type") or entry.get("node_kind")) == "module"
                and entry.get("qualified_name")
            }
            repo_prefix = repo_name_prefix(repo_root)
            local_packages = set(runtime_packaging.local_package_names(repo_root))

            sampling = sample_entities_from_db(
                nodes_data,
                resolver,
                artifact_conn,
                nodes,
                seed,
                progress_factory=progress_factory,
            )
            sampled = sampling.sampled

            print("Building file maps... ", end="", flush=True)
            parse_file_map, _ = prepare_parse_map(sampled, module_entries, resolver)
            print("done")

            parse_progress = None
            if progress_factory:
                parse_progress = progress_factory("Parsing files", len(parse_file_map))

            def _on_file_parsed(_file_path: str) -> None:
                if parse_progress:
                    parse_progress.advance(1)

            independent_results = parse_independent_files(
                repo_root, parse_file_map, on_file_parsed=_on_file_parsed
            )
            if parse_progress:
                parse_progress.close()

            normalized_edge_map, module_imports_by_prefix, _ = build_normalized_edge_maps(
                repo_root, independent_results
            )
            call_resolution = build_independent_call_resolution(
                independent_results,
                normalized_edge_map,
                full_module_names,
                repo_root,
                repo_prefix,
                local_packages,
                nodes_data,
            )
            reducer_source = ReducerEdgeSource(conn, repo_root, snapshot_id)
            db_source = DbEdgeSource(conn, artifact_conn, snapshot_id, resolver)

            validation_progress = None
            if progress_factory:
                validation_progress = progress_factory("Validating nodes", len(sampled))

            rows, out_of_contract_meta = evaluate_entities(
                sampled,
                independent_results,
                normalized_edge_map,
                module_imports_by_prefix,
                full_module_names,
                call_resolution,
                repo_root,
                repo_prefix,
                local_packages,
                reducer_source,
                db_source,
                validation_progress,
            )
            sampled_by_language: dict[str, int] = {}
            sampled_by_kind: dict[str, int] = {}
            for entity in sampled:
                sampled_by_language[entity.language] = (
                    int(sampled_by_language.get(entity.language, 0)) + 1
                )
                sampled_by_kind[entity.kind] = int(sampled_by_kind.get(entity.kind, 0)) + 1
            sampling_metadata = {
                "seed": int(seed),
                "requested_nodes": int(nodes),
                "sampled_nodes": len(sampled),
                "population_by_language": dict(sorted((sampling.population_by_language or {}).items())),
                "population_by_kind": dict(sorted((sampling.population_by_kind or {}).items())),
                "sampled_by_language": dict(sorted(sampled_by_language.items())),
                "sampled_by_kind": dict(sorted(sampled_by_kind.items())),
                "strata_counts": dict(sorted((sampling.strata_counts or {}).items())),
            }

    payload = _build_report_payload(
        repo_root=repo_root,
        rows=rows,
        out_of_contract_meta=out_of_contract_meta,
        sampling_metadata=sampling_metadata,
    )

    write_json(reports.json_path, payload)
    write_markdown(reports.md_path, render_summary(payload))
    print(f"Wrote: {reports.json_path}")
    print(f"Wrote: {reports.md_path}")
    return 0
