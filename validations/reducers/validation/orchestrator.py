# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import random
from pathlib import Path
from typing import List

from sciona.pipelines.progress import make_progress_factory
from sciona.runtime import packaging as runtime_packaging
from sciona.runtime.paths import repo_name_prefix

from . import config
from .contract_spec import get_validation_contract
from .db_adapter import list_nodes_from_artifacts, open_artifact_db
from .evaluation import (
    DbEdgeSource,
    ReducerEdgeSource,
    ResolverCache,
    build_normalized_edge_maps,
    coverage_by_language,
    evaluate_entities,
    prepare_parse_map,
    sample_entities_from_db,
)
from .evaluation_parse import parse_independent_files
from .evaluation_resolution import build_independent_call_resolution
from .invariants import basket_split_checks, evaluate_invariants, filter_contract_checks
from .import_contract import resolve_import_contract
from .out_of_contract import aggregate_breakdown
from .report import render_summary, write_json, write_markdown
from .sciona_adapter import get_snapshot_id, open_core_db
from .stability import independent_results_hash
from .stats import edge_type_breakdown, failure_examples, micro
from .taxonomy import (
    METRIC_DEFINITIONS,
    REPORT_SCHEMA_VERSION,
    divergence_index,
    overreach_rate,
    weighted_quality,
)

def _typescript_relative_index_contract_check(contract: dict) -> bool:
    language_spec = (
        (contract.get("imports") or {}).get("languages") or {}
    ).get("typescript", {})
    if language_spec.get("resolver") != "typescript_normalize":
        return True
    resolved = resolve_import_contract(
        raw_target="./api",
        file_path="pkg/main.ts",
        module_qname="fixture.pkg.main",
        language="typescript",
        contract=contract,
        module_names={"fixture.pkg.api.index"},
        repo_root=Path("/tmp/fixture"),
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    return resolved == "fixture.pkg.api.index"


def _select_threshold_profile(rows: list[dict]) -> tuple[str, dict]:
    languages = {row.get("language") for row in rows if row.get("language")}
    profile = "multi_language" if len(languages) > 1 else "single_language"
    thresholds = config.PROFILE_THRESHOLDS.get(profile, config.DEFAULT_THRESHOLDS)
    return profile, dict(thresholds)


def _bootstrap_micro_ci(
    rows: list[dict],
    metric_key: str,
    *,
    seed: int,
    rounds: int = 300,
) -> dict:
    metric_rows = [row for row in rows if row.get(metric_key)]
    if not metric_rows:
        return {"precision_ci95": None, "recall_ci95": None, "n": 0}
    rng = random.Random(seed)
    precisions: list[float] = []
    recalls: list[float] = []
    n = len(metric_rows)
    for _ in range(rounds):
        sample = [metric_rows[rng.randrange(n)] for _ in range(n)]
        m = micro(sample, metric_key)
        if m.get("precision") is not None:
            precisions.append(float(m["precision"]))
        if m.get("recall") is not None:
            recalls.append(float(m["recall"]))
    def _ci(values: list[float]) -> list[float] | None:
        if not values:
            return None
        values = sorted(values)
        lo = values[int(0.025 * (len(values) - 1))]
        hi = values[int(0.975 * (len(values) - 1))]
        return [lo, hi]
    return {"precision_ci95": _ci(precisions), "recall_ci95": _ci(recalls), "n": n}


def _aggregate_reason_recall(rows: list[dict], metric_key: str) -> dict:
    totals: dict[str, dict] = {}
    for row in rows:
        by_reason = row.get(metric_key) or {}
        for reason, bucket in by_reason.items():
            entry = totals.setdefault(reason, {"tp": 0, "fn": 0})
            entry["tp"] += int(bucket.get("tp") or 0)
            entry["fn"] += int(bucket.get("fn") or 0)
    out: dict[str, dict] = {}
    for reason, bucket in totals.items():
        tp = bucket["tp"]
        fn = bucket["fn"]
        den = tp + fn
        out[reason] = {"tp": tp, "fn": fn, "recall": (tp / den) if den else None}
    return out


def _limitation_edge_census(rows: list[dict]) -> dict:
    by_reason: dict[str, int] = {}
    by_language: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_language_kind: dict[str, dict[str, int]] = {}
    by_language_kind_reason: dict[str, dict[str, dict[str, int]]] = {}
    for row in rows:
        language = row.get("language") or "unknown"
        kind = row.get("kind") or "unknown"
        included_counts = row.get("included_limitation_by_reason") or {}
        included_edges = row.get("independent_static_limitation_by_reason") or {}
        reasons = set(included_counts) | set(included_edges)
        for reason in reasons:
            if reason in included_edges:
                count = len(included_edges.get(reason) or [])
            else:
                count = int(included_counts.get(reason) or 0)
            if count <= 0:
                continue
            by_reason[reason] = by_reason.get(reason, 0) + count
            by_language[language] = by_language.get(language, 0) + count
            by_kind[kind] = by_kind.get(kind, 0) + count
            by_language_kind.setdefault(language, {})
            by_language_kind[language][kind] = by_language_kind[language].get(kind, 0) + count
            by_language_kind_reason.setdefault(language, {})
            by_language_kind_reason[language].setdefault(kind, {})
            by_language_kind_reason[language][kind][reason] = (
                by_language_kind_reason[language][kind].get(reason, 0) + count
            )
    return {
        "total": int(sum(by_reason.values())),
        "by_reason": by_reason,
        "by_language": by_language,
        "by_kind": by_kind,
        "by_language_and_kind": by_language_kind,
        "by_language_kind_reason": by_language_kind_reason,
    }


def _contract_truncation_profile(rows: list[dict], *, top_k: int = 10) -> dict:
    modules: dict[str, int] = {}
    classes: dict[str, int] = {}
    entities: dict[str, int] = {}
    for row in rows:
        count = int(row.get("included_limitation_count") or 0)
        if count <= 0:
            continue
        entity = row.get("entity") or ""
        module = row.get("module_qualified_name") or ""
        kind = row.get("kind") or ""
        entities[entity] = entities.get(entity, 0) + count
        if module:
            modules[module] = modules.get(module, 0) + count
        if kind == "class" and entity:
            classes[entity] = classes.get(entity, 0) + count

    def _rank(counter: dict[str, int]) -> list[dict]:
        return [
            {"name": name, "limitation_edges": value}
            for name, value in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:top_k]
        ]

    return {
        "top_modules": _rank(modules),
        "top_classes": _rank(classes),
        "top_entities": _rank(entities),
    }


def _resolution_failure_taxonomy(rows: list[dict]) -> dict:
    dropped: dict[str, int] = {}
    accepted: dict[str, int] = {}
    candidate_histogram: dict[str, int] = {}
    for row in rows:
        for reason, count in (row.get("strict_contract_dropped_by_reason") or {}).items():
            dropped[reason] = dropped.get(reason, 0) + int(count or 0)
        for provenance, count in (row.get("strict_contract_accepted_by_provenance") or {}).items():
            accepted[provenance] = accepted.get(provenance, 0) + int(count or 0)
        for bucket, count in (row.get("strict_contract_candidate_count_histogram") or {}).items():
            candidate_histogram[bucket] = candidate_histogram.get(bucket, 0) + int(count or 0)
    return {
        "strict_contract_dropped_by_reason": dropped,
        "strict_contract_accepted_by_provenance": accepted,
        "strict_contract_candidate_count_histogram": candidate_histogram,
    }


def _contract_leakage_rate(reason_overlap: dict[str, dict]) -> dict:
    by_reason: dict[str, float | None] = {}
    tp_total = 0
    fn_total = 0
    for reason, bucket in reason_overlap.items():
        tp = int(bucket.get("tp") or 0)
        fn = int(bucket.get("fn") or 0)
        den = tp + fn
        by_reason[reason] = (tp / den) if den else None
        tp_total += tp
        fn_total += fn
    den_total = tp_total + fn_total
    return {
        "overall": (tp_total / den_total) if den_total else None,
        "tp": tp_total,
        "fn": fn_total,
        "by_reason": by_reason,
        "note": "Represents limitation-edge overlap with strict-resolved core edges; non-zero values indicate boundary leakage/fuzziness.",
    }


def _merge_nested_counter(
    target: dict[str, int], payload: dict[str, int] | None
) -> None:
    for key, value in (payload or {}).items():
        target[key] = target.get(key, 0) + int(value or 0)


def _parity_attribution(rows: list[dict]) -> dict:
    def _block(subset: list[dict]) -> dict:
        independent_dropped: dict[str, int] = {}
        independent_accepted: dict[str, int] = {}
        core_dropped: dict[str, int] = {}
        core_accepted: dict[str, int] = {}
        mismatch_totals = {
            "independent_overprojection": 0,
            "core_missed_resolution": 0,
            "core_overresolution": 0,
            "normalization_contract_mismatch": 0,
        }
        row_cause = {
            "independent_candidate_gap_dominant": 0,
            "core_selector_gap_dominant": 0,
            "balanced_or_none": 0,
        }
        for row in subset:
            _merge_nested_counter(
                independent_dropped, row.get("strict_contract_dropped_by_reason")
            )
            _merge_nested_counter(
                independent_accepted, row.get("strict_contract_accepted_by_provenance")
            )
            core_diag = row.get("core_call_resolution_diagnostics") or {}
            _merge_nested_counter(core_dropped, core_diag.get("dropped_by_reason"))
            _merge_nested_counter(core_accepted, core_diag.get("accepted_by_provenance"))
            mismatch = row.get("mismatch_attribution") or {}
            for key in mismatch_totals:
                mismatch_totals[key] += int(mismatch.get(key) or 0)
            independent_gap = int(mismatch.get("independent_overprojection") or 0)
            core_gap = int(mismatch.get("core_overresolution") or 0)
            if independent_gap > core_gap:
                row_cause["independent_candidate_gap_dominant"] += 1
            elif core_gap > independent_gap:
                row_cause["core_selector_gap_dominant"] += 1
            else:
                row_cause["balanced_or_none"] += 1
        independent_candidate_pressure = (
            int(independent_dropped.get("no_candidates") or 0)
            + int(independent_dropped.get("unique_without_provenance") or 0)
        )
        core_selector_pressure = sum(int(v or 0) for v in core_dropped.values())
        return {
            "independent_candidate_set": {
                "accepted_by_provenance": independent_accepted,
                "dropped_by_reason": independent_dropped,
                "candidate_pressure": independent_candidate_pressure,
            },
            "core_selector": {
                "accepted_by_provenance": core_accepted,
                "dropped_by_reason": core_dropped,
                "selector_pressure": core_selector_pressure,
            },
            "final_edge_parity": mismatch_totals,
            "row_dominant_cause": row_cause,
        }

    out = {"repo_totals": _block(rows), "by_language_and_kind": {}}
    languages = sorted({row.get("language") for row in rows if row.get("language")})
    for language in languages:
        by_kind: dict[str, dict] = {}
        for kind in ("module", "class", "function", "method"):
            subset = [
                row
                for row in rows
                if row.get("language") == language and row.get("kind") == kind
            ]
            by_kind[kind] = _block(subset)
        out["by_language_and_kind"][language] = by_kind
    return out


def _strict_contract_policy_violations(
    rows: list[dict],
    *,
    mode: str,
    allowed_acceptance: set[str],
    allowed_drop_reasons: set[str],
) -> dict:
    mode_mismatch_count = 0
    accepted_violations: dict[str, int] = {}
    dropped_violations: dict[str, int] = {}
    for row in rows:
        if row.get("strict_contract_mode") != mode:
            mode_mismatch_count += 1
        accepted = row.get("strict_contract_accepted_by_provenance") or {}
        dropped = row.get("strict_contract_dropped_by_reason") or {}
        for key, value in accepted.items():
            if key not in allowed_acceptance:
                accepted_violations[key] = accepted_violations.get(key, 0) + int(value or 0)
        for key, value in dropped.items():
            if key not in allowed_drop_reasons:
                dropped_violations[key] = dropped_violations.get(key, 0) + int(value or 0)
    return {
        "mode_mismatch_count": mode_mismatch_count,
        "accepted_violations": accepted_violations,
        "dropped_violations": dropped_violations,
    }


def _build_action_priority_board(
    *,
    strict_by_kind: dict,
    strict_overreach: float | None,
    strict_recall: float | None,
    expanded_full_recall: float | None,
    reasoning_reliability: float | None,
) -> list[dict]:
    board: list[dict] = []
    method = strict_by_kind.get("method") or {}
    function = strict_by_kind.get("function") or {}
    if method.get("recall") is not None and float(method["recall"]) < 0.85:
        board.append(
            {
                "priority": "high",
                "area": "core_analysis",
                "issue": "method_recall_gap",
                "evidence": {"method_recall": method.get("recall")},
            }
        )
    if method.get("precision") is not None and float(method["precision"]) < 0.85:
        board.append(
            {
                "priority": "high",
                "area": "core_analysis",
                "issue": "method_precision_gap",
                "evidence": {"method_precision": method.get("precision")},
            }
        )
    if function.get("recall") is not None and float(function["recall"]) < 0.90:
        board.append(
            {
                "priority": "medium",
                "area": "core_analysis",
                "issue": "function_recall_gap",
                "evidence": {"function_recall": function.get("recall")},
            }
        )
    if strict_overreach is not None and strict_overreach > 0.05:
        board.append(
            {
                "priority": "high",
                "area": "core_analysis",
                "issue": "strict_overreach_elevated",
                "evidence": {"strict_overreach_rate": strict_overreach},
            }
        )
    if (
        strict_recall is not None
        and expanded_full_recall is not None
        and (strict_recall - expanded_full_recall) > 0.04
    ):
        board.append(
            {
                "priority": "medium",
                "area": "validation_workflow",
                "issue": "strict_to_expanded_recall_drop",
                "evidence": {
                    "strict_recall": strict_recall,
                    "expanded_full_recall": expanded_full_recall,
                    "delta": strict_recall - expanded_full_recall,
                },
            }
        )
    if reasoning_reliability is not None and reasoning_reliability < 0.70:
        board.append(
            {
                "priority": "medium",
                "area": "core_analysis",
                "issue": "reasoning_reliability_low",
                "evidence": {"reasoning_structural_reliability": reasoning_reliability},
            }
        )
    rank = {"high": 0, "medium": 1, "low": 2}
    board.sort(key=lambda item: rank.get(item["priority"], 9))
    return board


def run_validation(
    *,
    repo_root: Path,
    nodes: int,
    seed: int,
    stability_runs: int,
) -> int:
    repo_root = repo_root.resolve()
    reports = config.report_paths(repo_root)
    contract = get_validation_contract()

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
            parse_file_map, overview_errors = prepare_parse_map(
                sampled, module_entries, resolver
            )
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

            (
                normalized_edge_map,
                module_imports_by_prefix,
                scoped_normalization_ok,
            ) = build_normalized_edge_maps(repo_root, independent_results)
            stability_score = None
            stability_error = None
            stability_hashes: List[str] = []
            try:
                runs = max(1, int(stability_runs))
                stability_hashes.append(
                    independent_results_hash(independent_results, normalized_edge_map)
                )
                for _ in range(1, runs):
                    rerun_results = parse_independent_files(
                        repo_root, parse_file_map, on_file_parsed=None
                    )
                    rerun_normalized_map, _, _ = build_normalized_edge_maps(
                        repo_root, rerun_results
                    )
                    stability_hashes.append(
                        independent_results_hash(rerun_results, rerun_normalized_map)
                    )
                stability_score = 1.0 if len(set(stability_hashes)) == 1 else 0.0
            except Exception as exc:
                stability_error = str(exc)
            call_resolution = build_independent_call_resolution(
                independent_results,
                normalized_edge_map,
                full_module_names,
                contract,
                repo_root,
                repo_prefix,
                local_packages,
            )
            coverage = coverage_by_language(independent_results)
            reducer_source = ReducerEdgeSource(conn, repo_root, snapshot_id)
            db_source = DbEdgeSource(conn, artifact_conn, snapshot_id, resolver)
            validation_progress = None
            if progress_factory:
                validation_progress = progress_factory("Validating nodes", len(sampled))
            rows, out_of_contract_meta, total_files, parse_ok_files = evaluate_entities(
                sampled,
                independent_results,
                normalized_edge_map,
                module_imports_by_prefix,
                full_module_names,
                call_resolution,
                contract,
                repo_root,
                repo_prefix,
                local_packages,
                reducer_source,
                db_source,
                validation_progress,
            )

    scored_rows_reducer_vs_contract = [
        row for row in rows if row.get("metrics_reducer_vs_contract") is not None
    ]
    scored_rows_reducer_vs_db = [
        row for row in rows if row.get("metrics_reducer_vs_db") is not None
    ]
    scored_rows_db_vs_contract = [
        row for row in rows if row.get("metrics_db_vs_contract") is not None
    ]
    scored_rows_reducer_vs_enriched = [
        row for row in rows if row.get("metrics_reducer_vs_enriched_truth") is not None
    ]
    scored_rows_db_vs_enriched = [
        row for row in rows if row.get("metrics_db_vs_enriched_truth") is not None
    ]
    scored_rows_reducer_vs_expanded_high = [
        row for row in rows if row.get("metrics_reducer_vs_expanded_high_conf") is not None
    ]
    scored_rows_reducer_vs_expanded_full = [
        row for row in rows if row.get("metrics_reducer_vs_expanded_full") is not None
    ]
    scored_rows_db_vs_expanded_high = [
        row for row in rows if row.get("metrics_db_vs_expanded_high_conf") is not None
    ]
    scored_rows_db_vs_expanded_full = [
        row for row in rows if row.get("metrics_db_vs_expanded_full") is not None
    ]

    reducer_full_entities = {row["entity"] for row in scored_rows_reducer_vs_contract}
    db_full_entities = {row["entity"] for row in scored_rows_db_vs_contract}

    reducer_vs_db_micro = micro(scored_rows_reducer_vs_db, "metrics_reducer_vs_db")
    reducer_vs_contract_micro = micro(
        scored_rows_reducer_vs_contract, "metrics_reducer_vs_contract"
    )
    db_vs_contract_micro = micro(scored_rows_db_vs_contract, "metrics_db_vs_contract")
    reducer_vs_enriched_micro = micro(
        scored_rows_reducer_vs_enriched, "metrics_reducer_vs_enriched_truth"
    )
    db_vs_enriched_micro = micro(scored_rows_db_vs_enriched, "metrics_db_vs_enriched_truth")
    reducer_vs_expanded_high_micro = micro(
        scored_rows_reducer_vs_expanded_high, "metrics_reducer_vs_expanded_high_conf"
    )
    reducer_vs_expanded_full_micro = micro(
        scored_rows_reducer_vs_expanded_full, "metrics_reducer_vs_expanded_full"
    )
    db_vs_expanded_high_micro = micro(
        scored_rows_db_vs_expanded_high, "metrics_db_vs_expanded_high_conf"
    )
    db_vs_expanded_full_micro = micro(
        scored_rows_db_vs_expanded_full, "metrics_db_vs_expanded_full"
    )
    contract_truth_pure_ok, contract_truth_resolved_ok, no_duplicate_contract_edges = (
        filter_contract_checks(rows)
    )
    basket_partition_ok, basket_counts_reconciled_ok = basket_split_checks(rows)
    class_rows_parse_ok = [
        row
        for row in rows
        if row.get("kind") == "class"
        and row.get("ground_truth_parse_ok")
        and row.get("class_has_methods")
    ]
    class_rows_matchable = [
        row for row in class_rows_parse_ok if not row.get("class_truth_unreliable")
    ]
    class_rows_nonempty = [
        row for row in class_rows_parse_ok if not row.get("class_truth_empty_while_parse_ok")
    ]
    class_truth_nonempty_rate = (
        (len(class_rows_nonempty) / len(class_rows_parse_ok))
        if class_rows_parse_ok
        else 1.0
    )
    class_truth_match_rate = (
        (len(class_rows_matchable) / len(class_rows_parse_ok))
        if class_rows_parse_ok
        else 1.0
    )
    class_rows_unreliable = [
        row for row in class_rows_parse_ok if row.get("class_truth_unreliable")
    ]

    def _merge_counter_maps(target: dict[str, int], source: dict | None) -> None:
        if not source:
            return
        for key, value in source.items():
            try:
                amount = int(value)
            except Exception:
                continue
            target[key] = int(target.get(key, 0)) + amount

    def _resolution_counter_block(rows_subset: list[dict]) -> dict[str, dict[str, int]]:
        accepted: dict[str, int] = {}
        dropped: dict[str, int] = {}
        candidate_histogram: dict[str, int] = {}
        record_drops: dict[str, int] = {}
        for row in rows_subset:
            diag = row.get("core_call_resolution_diagnostics") or {}
            if not isinstance(diag, dict):
                continue
            _merge_counter_maps(accepted, diag.get("accepted_by_provenance"))
            _merge_counter_maps(dropped, diag.get("dropped_by_reason"))
            _merge_counter_maps(candidate_histogram, diag.get("candidate_count_histogram"))
            _merge_counter_maps(record_drops, diag.get("record_drops"))
        return {
            "accepted_by_provenance": accepted,
            "dropped_by_reason": dropped,
            "candidate_count_histogram": candidate_histogram,
            "record_drops": record_drops,
        }

    call_resolution_diagnostics_summary = _resolution_counter_block(rows)
    call_resolution_diagnostics_by_language_kind: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
    for language in sorted({row.get("language") for row in rows if row.get("language")}):
        by_kind: dict[str, dict[str, dict[str, int]]] = {}
        for kind in ("module", "class", "function", "method"):
            subset = [
                row
                for row in rows
                if row.get("language") == language and row.get("kind") == kind
            ]
            by_kind[kind] = _resolution_counter_block(subset)
        call_resolution_diagnostics_by_language_kind[language] = by_kind
    strict_contract_accepted: dict[str, int] = {}
    strict_contract_dropped: dict[str, int] = {}
    strict_contract_candidate_histogram: dict[str, int] = {}
    for row in rows:
        _merge_counter_maps(
            strict_contract_accepted,
            row.get("strict_contract_accepted_by_provenance"),
        )
        _merge_counter_maps(
            strict_contract_dropped,
            row.get("strict_contract_dropped_by_reason"),
        )
        _merge_counter_maps(
            strict_contract_candidate_histogram,
            row.get("strict_contract_candidate_count_histogram"),
        )

    def _micro_by_kind(metric_key: str) -> dict[str, dict]:
        by_kind: dict[str, dict] = {}
        for kind in ("module", "class", "function", "method"):
            subset = [row for row in rows if row.get("kind") == kind and row.get(metric_key)]
            by_kind[kind] = micro(subset, metric_key) if subset else {}
        return by_kind

    def _micro_by_language(metric_key: str) -> dict[str, dict]:
        by_language: dict[str, dict] = {}
        languages = sorted(
            {
                row.get("language")
                for row in rows
                if row.get("language") and row.get(metric_key)
            }
        )
        for language in languages:
            subset = [
                row
                for row in rows
                if row.get("language") == language and row.get(metric_key)
            ]
            by_language[language] = micro(subset, metric_key) if subset else {}
        return by_language

    def _micro_by_language_and_kind(metric_key: str) -> dict[str, dict[str, dict]]:
        by_language_kind: dict[str, dict[str, dict]] = {}
        languages = sorted({row.get("language") for row in rows if row.get("language")})
        for language in languages:
            by_kind: dict[str, dict] = {}
            for kind in ("module", "class", "function", "method"):
                subset = [
                    row
                    for row in rows
                    if row.get("language") == language
                    and row.get("kind") == kind
                    and row.get(metric_key)
                ]
                by_kind[kind] = micro(subset, metric_key) if subset else {}
            by_language_kind[language] = by_kind
        return by_language_kind

    def _call_form_recall(metric_key: str) -> dict[str, dict]:
        totals = {
            "direct": {"tp": 0, "fn": 0},
            "member": {"tp": 0, "fn": 0},
        }
        for row in rows:
            metrics = row.get(metric_key) or {}
            for form in ("direct", "member"):
                bucket = metrics.get(form) or {}
                totals[form]["tp"] += int(bucket.get("tp") or 0)
                totals[form]["fn"] += int(bucket.get("fn") or 0)
        result: dict[str, dict] = {}
        for form in ("direct", "member"):
            tp = totals[form]["tp"]
            fn = totals[form]["fn"]
            den = tp + fn
            result[form] = {
                "tp": tp,
                "fn": fn,
                "recall": (tp / den) if den else None,
            }
        return result

    def _edge_key(edge: dict) -> tuple[str, str]:
        return (
            edge.get("caller") or "",
            edge.get("callee_qname") or edge.get("callee") or "",
        )

    def _classify_mismatches(row: dict) -> dict:
        expected = row.get("contract_truth_edges") or []
        reducer = row.get("reducer_edges") or []
        db = row.get("db_edges") or []
        exp_set = {_edge_key(edge) for edge in expected}
        reducer_set = {_edge_key(edge) for edge in reducer}
        db_set = {_edge_key(edge) for edge in db}
        missing = exp_set - reducer_set
        extra = reducer_set - exp_set
        attribution = {
            "independent_overprojection": 0,
            "core_missed_resolution": 0,
            "core_overresolution": 0,
            "normalization_contract_mismatch": 0,
        }
        for edge in missing:
            if edge in db_set:
                attribution["normalization_contract_mismatch"] += 1
            else:
                attribution["independent_overprojection"] += 1
        for edge in extra:
            if edge in db_set:
                attribution["core_overresolution"] += 1
            else:
                attribution["normalization_contract_mismatch"] += 1
        return {
            "attribution": attribution,
            "missing_count": len(missing),
            "extra_count": len(extra),
        }

    contract_recall = reducer_vs_contract_micro.get("recall")
    static_overreach_rate = overreach_rate(reducer_vs_contract_micro)
    call_form_reducer_vs_contract = _call_form_recall(
        "metrics_reducer_vs_contract_by_call_form"
    )
    member_call_recall = (call_form_reducer_vs_contract.get("member") or {}).get(
        "recall"
    )
    member_call_bucket = call_form_reducer_vs_contract.get("member") or {}
    member_call_recall_applicable = (
        int(member_call_bucket.get("tp") or 0) + int(member_call_bucket.get("fn") or 0)
    ) > 0
    strict_policy = config.STRICT_CONTRACT_POLICY
    expanded_policy = config.EXPANDED_TRUTH_POLICY
    scope_exclusions = set(expanded_policy.get("scope_exclusions") or [])
    limitation_focus = set(expanded_policy.get("limitation_focus") or [])
    limitation_scope_clean_ok = True
    limitation_taxonomy_stable_ok = True
    strict_drop_taxonomy_stable_ok = True
    allowed_drop_reasons = set(strict_policy.get("allowed_drop_reasons") or [])
    for row in rows:
        included_reasons = set((row.get("included_limitation_by_reason") or {}).keys())
        if included_reasons & scope_exclusions:
            limitation_scope_clean_ok = False
        if any(reason not in limitation_focus for reason in included_reasons):
            limitation_taxonomy_stable_ok = False
        dropped_reasons = set((row.get("strict_contract_dropped_by_reason") or {}).keys())
        if any(reason not in allowed_drop_reasons for reason in dropped_reasons):
            strict_drop_taxonomy_stable_ok = False

    policy_violations = _strict_contract_policy_violations(
        rows,
        mode=str(strict_policy.get("mode") or config.STRICT_CONTRACT_MODE),
        allowed_acceptance=set(strict_policy.get("allowed_acceptance") or []),
        allowed_drop_reasons=set(strict_policy.get("allowed_drop_reasons") or []),
    )
    strict_contract_parity_ok = (
        policy_violations["mode_mismatch_count"] == 0
        and not policy_violations["accepted_violations"]
        and not policy_violations["dropped_violations"]
    )
    profile_name, thresholds = _select_threshold_profile(rows)
    invariants = evaluate_invariants(
        rows,
        reducer_full_entities=reducer_full_entities,
        db_full_entities=db_full_entities,
        reducer_full_micro=reducer_vs_contract_micro,
        db_full_micro=db_vs_contract_micro,
        parse_ok_files=parse_ok_files,
        total_files=total_files,
        contract_truth_pure_ok=contract_truth_pure_ok,
        contract_truth_resolved_ok=contract_truth_resolved_ok,
        parser_deterministic=(stability_score == 1.0),
        no_duplicate_contract_edges=no_duplicate_contract_edges,
        basket_partition_ok=basket_partition_ok,
        basket_counts_reconciled_ok=basket_counts_reconciled_ok,
        typescript_relative_index_contract_ok=_typescript_relative_index_contract_check(contract),
        class_truth_nonempty_rate_ok=(
            class_truth_nonempty_rate >= thresholds["class_truth_nonempty_rate_min"]
        ),
        class_truth_match_rate_ok=(
            class_truth_match_rate >= thresholds["class_truth_match_rate_min"]
        ),
        scoped_call_normalization_ok=scoped_normalization_ok,
        strict_contract_parity_ok=strict_contract_parity_ok,
        limitation_scope_clean_ok=limitation_scope_clean_ok,
        limitation_taxonomy_stable_ok=limitation_taxonomy_stable_ok,
        strict_drop_taxonomy_stable_ok=strict_drop_taxonomy_stable_ok,
        contract_recall_ok=(
            contract_recall is not None and contract_recall >= thresholds["contract_recall_min"]
        ),
        overreach_rate_ok=(
            static_overreach_rate is not None
            and static_overreach_rate <= thresholds["overreach_rate_max"]
        ),
        member_call_recall_ok=(
            member_call_recall is not None
            and member_call_recall >= thresholds["member_call_recall_min"]
        ) if member_call_recall_applicable else None,
    )

    failure_examples_contract = failure_examples(
        scored_rows_reducer_vs_contract, "metrics_reducer_vs_contract"
    )
    edge_breakdown_contract = edge_type_breakdown(
        scored_rows_reducer_vs_contract, "metrics_reducer_vs_contract"
    )
    calls_breakdown = edge_breakdown_contract.get("calls", {})
    imports_breakdown = edge_breakdown_contract.get("imports", {})
    enriched_divergence_index = divergence_index(reducer_vs_enriched_micro)
    reason_recall_reducer = _aggregate_reason_recall(
        rows, "metrics_reducer_vs_expanded_by_reason"
    )
    reason_recall_db = _aggregate_reason_recall(rows, "metrics_db_vs_expanded_by_reason")
    limitation_edge_census = _limitation_edge_census(rows)
    contract_truncation_profile = _contract_truncation_profile(rows)
    resolution_failure_taxonomy = _resolution_failure_taxonomy(rows)
    contract_leakage_rate = _contract_leakage_rate(reason_recall_reducer)

    raw_call_total = sum(len(result.call_edges) for result in independent_results.values())
    raw_import_total = sum(len(result.import_edges) for result in independent_results.values())
    normalized_call_total = sum(
        len(edges[0]) for edges in normalized_edge_map.values()
    )
    normalized_import_total = sum(
        len(edges[1]) for edges in normalized_edge_map.values()
    )
    expected_total = sum(len(row.get("contract_truth_edges") or []) for row in rows)
    independent_limitation_total = sum(
        len(row.get("independent_static_limitation_edges") or [])
        for row in rows
    )
    contract_exclusion_total = sum(
        len(row.get("contract_exclusion_edges") or [])
        for row in rows
    )
    enriched_truth_total = sum(
        len(row.get("enriched_truth_edges") or [])
        for row in rows
    )
    expanded_high_total = sum(
        len(row.get("expanded_truth_edges_high_conf") or [])
        for row in rows
    )
    expanded_full_total = sum(
        len(row.get("expanded_truth_edges_full") or [])
        for row in rows
    )
    excluded_out_of_scope_total = sum(
        int(row.get("excluded_out_of_scope_count") or 0)
        for row in rows
    )
    included_limitation_total = sum(
        int(row.get("included_limitation_count") or 0)
        for row in rows
    )
    excluded_out_of_scope_by_reason: dict[str, int] = {}
    included_limitation_by_reason: dict[str, int] = {}
    for row in rows:
        excluded_counts = row.get("excluded_out_of_scope_by_reason") or {}
        included_counts = row.get("included_limitation_by_reason") or {}
        excluded_edges = row.get("contract_exclusion_by_reason") or {}
        included_edges = row.get("independent_static_limitation_by_reason") or {}
        excluded_reasons = set(excluded_counts) | set(excluded_edges)
        included_reasons = set(included_counts) | set(included_edges)
        for reason in excluded_reasons:
            count = (
                len(excluded_edges.get(reason) or [])
                if reason in excluded_edges
                else int(excluded_counts.get(reason) or 0)
            )
            excluded_out_of_scope_by_reason[reason] = (
                excluded_out_of_scope_by_reason.get(reason, 0) + int(count or 0)
            )
        for reason in included_reasons:
            count = (
                len(included_edges.get(reason) or [])
                if reason in included_edges
                else int(included_counts.get(reason) or 0)
            )
            included_limitation_by_reason[reason] = (
                included_limitation_by_reason.get(reason, 0) + int(count or 0)
            )
    reducer_edge_total = sum(len(row.get("reducer_edges") or []) for row in rows)
    attribution_totals = {
        "independent_overprojection": 0,
        "core_missed_resolution": 0,
        "core_overresolution": 0,
        "normalization_contract_mismatch": 0,
    }
    for row in rows:
        mismatch = _classify_mismatches(row)
        row["mismatch_attribution"] = mismatch["attribution"]
        row["mismatch_counts"] = {
            "missing_count": mismatch["missing_count"],
            "extra_count": mismatch["extra_count"],
        }
        for key, value in mismatch["attribution"].items():
            attribution_totals[key] += int(value or 0)
    parity_attribution = _parity_attribution(rows)

    summary = []
    summary.append(f"repo={repo_name_prefix(repo_root)}")
    summary.append(f"sampled_nodes={len(rows)}")
    summary.append(f"invariants_passed={invariants['passed']}")
    summary.append(f"static_contract_recall={contract_recall}")
    summary.append(f"static_overreach_rate={static_overreach_rate}")

    internal_hard_gate_keys = [
        "gate_reducer_db_exact",
        "gate_aligned_scoring",
        "gate_parse_coverage",
        "gate_contract_truth_pure",
        "gate_contract_truth_resolved",
        "gate_parser_deterministic",
        "gate_no_duplicate_contract_edges",
        "gate_basket_partition",
        "gate_basket_counts_reconciled",
        "gate_scoped_call_normalization",
        "gate_strict_contract_parity",
        "gate_limitation_scope_clean",
        "gate_limitation_taxonomy_stable",
        "gate_strict_drop_taxonomy_stable",
        "gate_equal_contract_metrics_when_exact",
    ]
    internal_valid = all(bool(invariants.get(key)) for key in internal_hard_gate_keys)
    semantic_divergence_index = divergence_index(reducer_vs_contract_micro)
    module_metrics = (_micro_by_kind("metrics_reducer_vs_contract") or {}).get("module") or {}
    function_metrics = (_micro_by_kind("metrics_reducer_vs_contract") or {}).get("function") or {}
    method_metrics = (_micro_by_kind("metrics_reducer_vs_contract") or {}).get("method") or {}
    navigation_weights = config.PROMPT_FITNESS_WEIGHTS["navigation"]
    reasoning_weights = config.PROMPT_FITNESS_WEIGHTS["reasoning"]
    navigation_reliability = weighted_quality(
        tp=int(module_metrics.get("tp") or 0),
        fp=int(module_metrics.get("fp") or 0),
        fn=int(module_metrics.get("fn") or 0),
        fp_weight=float(navigation_weights["fp_weight"]),
        fn_weight=float(navigation_weights["fn_weight"]),
    )
    reasoning_tp = int(function_metrics.get("tp") or 0) + int(method_metrics.get("tp") or 0)
    reasoning_fp = int(function_metrics.get("fp") or 0) + int(method_metrics.get("fp") or 0)
    reasoning_fn = int(function_metrics.get("fn") or 0) + int(method_metrics.get("fn") or 0)
    reasoning_reliability = weighted_quality(
        tp=reasoning_tp,
        fp=reasoning_fp,
        fn=reasoning_fn,
        fp_weight=float(reasoning_weights["fp_weight"]),
        fn_weight=float(reasoning_weights["fn_weight"]),
    )
    coupling_stability_index = (
        (1.0 - static_overreach_rate) if static_overreach_rate is not None else None
    )
    nav_fp_weight = float(navigation_weights["fp_weight"])
    nav_fn_weight = float(navigation_weights["fn_weight"])
    reason_fp_weight = float(reasoning_weights["fp_weight"])
    reason_fn_weight = float(reasoning_weights["fn_weight"])
    nav_penalty_fp = nav_fp_weight * int(module_metrics.get("fp") or 0)
    nav_penalty_fn = nav_fn_weight * int(module_metrics.get("fn") or 0)
    reason_penalty_fp = reason_fp_weight * reasoning_fp
    reason_penalty_fn = reason_fn_weight * reasoning_fn
    strict_by_kind = _micro_by_kind("metrics_reducer_vs_contract")
    action_priority_board = _build_action_priority_board(
        strict_by_kind=strict_by_kind,
        strict_overreach=static_overreach_rate,
        strict_recall=contract_recall,
        expanded_full_recall=reducer_vs_expanded_full_micro.get("recall"),
        reasoning_reliability=reasoning_reliability,
    )
    uncertainty_intervals = {
        "strict_contract_alignment": _bootstrap_micro_ci(
            rows, "metrics_reducer_vs_contract", seed=seed
        ),
        "expanded_full_alignment": _bootstrap_micro_ci(
            rows, "metrics_reducer_vs_expanded_full", seed=seed + 1
        ),
        "method_strict_alignment": _bootstrap_micro_ci(
            [row for row in rows if row.get("kind") == "method"],
            "metrics_reducer_vs_contract",
            seed=seed + 2,
        ),
    }

    payload = {
        "repo_root": str(repo_root),
        "snapshot_id": snapshot_id,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "summary": summary,
        "invariants": invariants,
        "metric_definitions": METRIC_DEFINITIONS,
        "core_metrics": {
            "static_contract_recall": contract_recall,
            "static_overreach_rate": static_overreach_rate,
            "overreach_count": reducer_vs_contract_micro["fp"],
            "reducer_edge_total": reducer_edge_total,
        },
        "internal_integrity": {
            "valid": internal_valid,
            "hard_gates": {key: invariants.get(key) for key in internal_hard_gate_keys},
            "projection": {
                "reducer_db_exact": invariants.get("gate_reducer_db_exact"),
                "aligned_scoring": invariants.get("gate_aligned_scoring"),
                "static_projection_precision": reducer_vs_db_micro.get("precision"),
                "static_projection_recall": reducer_vs_db_micro.get("recall"),
            },
            "determinism": {
                "parser_stability_score": stability_score,
                "gate_parser_deterministic": invariants.get("gate_parser_deterministic"),
            },
        },
        "static_contract_alignment": {
            "static_contract_precision": reducer_vs_contract_micro.get("precision"),
            "static_contract_recall": reducer_vs_contract_micro.get("recall"),
            "static_overreach_rate": static_overreach_rate,
            "static_divergence_index": semantic_divergence_index,
            "by_kind": _micro_by_kind("metrics_reducer_vs_contract"),
            "by_edge_type": edge_breakdown_contract,
            "call_form_recall": call_form_reducer_vs_contract,
            "uncertainty_intervals": {
                "micro": uncertainty_intervals["strict_contract_alignment"],
                "method": uncertainty_intervals["method_strict_alignment"],
            },
        },
        "enrichment_practical": {
            "prompt_reliability_version": config.PROMPT_RELIABILITY_VERSION,
            "navigation_structural_reliability": navigation_reliability,
            "reasoning_structural_reliability": reasoning_reliability,
            "coupling_stability_index": coupling_stability_index,
            "component_contributions": {
                "navigation": {
                    "tp": int(module_metrics.get("tp") or 0),
                    "fp": int(module_metrics.get("fp") or 0),
                    "fn": int(module_metrics.get("fn") or 0),
                    "penalty_fp": nav_penalty_fp,
                    "penalty_fn": nav_penalty_fn,
                    "denominator": int(module_metrics.get("tp") or 0) + nav_penalty_fp + nav_penalty_fn,
                },
                "reasoning": {
                    "tp": reasoning_tp,
                    "fp": reasoning_fp,
                    "fn": reasoning_fn,
                    "penalty_fp": reason_penalty_fp,
                    "penalty_fn": reason_penalty_fn,
                    "denominator": reasoning_tp + reason_penalty_fp + reason_penalty_fn,
                },
            },
            "noise_signal": {
                "dynamic_or_unresolved_limitation_edges": independent_limitation_total,
                "contract_edges": expected_total,
                "enrichment_noise_ratio": (
                    (independent_limitation_total / (expected_total + independent_limitation_total))
                    if (expected_total + independent_limitation_total)
                    else None
                ),
            },
            "edge_mix": {
                "calls": calls_breakdown,
                "imports": imports_breakdown,
            },
            "weights": config.PROMPT_FITNESS_WEIGHTS,
        },
        "enriched_truth_alignment": {
            "reducer_vs_enriched_truth_precision": reducer_vs_enriched_micro.get("precision"),
            "reducer_vs_enriched_truth_recall": reducer_vs_enriched_micro.get("recall"),
            "db_vs_enriched_truth_precision": db_vs_enriched_micro.get("precision"),
            "db_vs_enriched_truth_recall": db_vs_enriched_micro.get("recall"),
            "reducer_vs_enriched_truth_divergence_index": enriched_divergence_index,
            "inclusion_policy": {
                "base": "contract_truth_edges + limitation_edges",
                "scope_exclusions": config.EXPANDED_TRUTH_POLICY.get("scope_exclusions"),
                "limitation_focus": config.EXPANDED_TRUTH_POLICY.get("limitation_focus"),
                "confidence_tiers": config.EXPANDED_TRUTH_POLICY.get("confidence_tiers"),
                "notes": "Expanded truth is diagnostic-only and non-gating.",
            },
            "tiers": {
                "high_conf": {
                    "reducer_precision": reducer_vs_expanded_high_micro.get("precision"),
                    "reducer_recall": reducer_vs_expanded_high_micro.get("recall"),
                    "db_precision": db_vs_expanded_high_micro.get("precision"),
                    "db_recall": db_vs_expanded_high_micro.get("recall"),
                    "divergence_index": divergence_index(reducer_vs_expanded_high_micro),
                },
                "full": {
                    "reducer_precision": reducer_vs_expanded_full_micro.get("precision"),
                    "reducer_recall": reducer_vs_expanded_full_micro.get("recall"),
                    "db_precision": db_vs_expanded_full_micro.get("precision"),
                    "db_recall": db_vs_expanded_full_micro.get("recall"),
                    "divergence_index": divergence_index(reducer_vs_expanded_full_micro),
                },
            },
            "tier_edge_counts": {
                "high_conf_edges": expanded_high_total,
                "full_edges": expanded_full_total,
            },
            "scope_split_counts": {
                "excluded_out_of_scope_edges": excluded_out_of_scope_total,
                "included_limitation_edges": included_limitation_total,
                "excluded_out_of_scope_by_reason": excluded_out_of_scope_by_reason,
                "included_limitation_by_reason": included_limitation_by_reason,
            },
            "by_kind": _micro_by_kind("metrics_reducer_vs_enriched_truth"),
            "by_edge_type": edge_type_breakdown(
                scored_rows_reducer_vs_enriched, "metrics_reducer_vs_enriched_truth"
            ),
            "uncertainty_intervals": {
                "micro": uncertainty_intervals["expanded_full_alignment"],
            },
        },
        "contract_boundary": {
            "description": "Diagnostic profile of strict-contract truncation boundaries. Descriptive-only and non-gating.",
            "inclusion_policy": {
                "base": "contract_truth_edges + limitation_edges",
                "scope_exclusions": config.EXPANDED_TRUTH_POLICY.get("scope_exclusions"),
                "limitation_focus": config.EXPANDED_TRUTH_POLICY.get("limitation_focus"),
                "confidence_tiers": config.EXPANDED_TRUTH_POLICY.get("confidence_tiers"),
            },
            "limitation_edge_counts": {
                "high_conf_edges": expanded_high_total,
                "full_edges": expanded_full_total,
                "excluded_out_of_scope_edges": excluded_out_of_scope_total,
                "included_limitation_edges": included_limitation_total,
                "independent_static_limitation_edges": independent_limitation_total,
                "contract_exclusion_edges": contract_exclusion_total,
                "excluded_out_of_scope_by_reason": excluded_out_of_scope_by_reason,
                "included_limitation_by_reason": included_limitation_by_reason,
            },
            "envelopes": {
                "independent_static_limitations": {
                    "edge_count": independent_limitation_total,
                    "by_reason": included_limitation_by_reason,
                },
                "contract_exclusions": {
                    "edge_count": contract_exclusion_total,
                    "by_reason": excluded_out_of_scope_by_reason,
                },
            },
            "limitation_edge_census": limitation_edge_census,
            "contract_truncation_profile": contract_truncation_profile,
            "resolution_failure_taxonomy": resolution_failure_taxonomy,
            "contract_leakage_rate": contract_leakage_rate,
            "overlap_diagnostics": {
                "reducer": reason_recall_reducer,
                "db": reason_recall_db,
                "note": "Overlap is diagnostic and does not imply expected strict-contract recall of limitation edges.",
            },
        },
        "micro_metrics": {
            "reducer_vs_db": reducer_vs_db_micro,
            "db_vs_contract_truth": db_vs_contract_micro,
            "reducer_vs_contract_truth": reducer_vs_contract_micro,
            "reducer_vs_enriched_truth": reducer_vs_enriched_micro,
            "db_vs_enriched_truth": db_vs_enriched_micro,
            "reducer_vs_expanded_high_conf": reducer_vs_expanded_high_micro,
            "reducer_vs_expanded_full": reducer_vs_expanded_full_micro,
            "db_vs_expanded_high_conf": db_vs_expanded_high_micro,
            "db_vs_expanded_full": db_vs_expanded_full_micro,
        },
        "micro_metrics_by_kind": {
            "reducer_vs_db": _micro_by_kind("metrics_reducer_vs_db"),
            "db_vs_contract_truth": _micro_by_kind("metrics_db_vs_contract"),
            "reducer_vs_contract_truth": _micro_by_kind("metrics_reducer_vs_contract"),
            "reducer_vs_enriched_truth": _micro_by_kind("metrics_reducer_vs_enriched_truth"),
            "db_vs_enriched_truth": _micro_by_kind("metrics_db_vs_enriched_truth"),
            "reducer_vs_expanded_high_conf": _micro_by_kind("metrics_reducer_vs_expanded_high_conf"),
            "reducer_vs_expanded_full": _micro_by_kind("metrics_reducer_vs_expanded_full"),
            "db_vs_expanded_high_conf": _micro_by_kind("metrics_db_vs_expanded_high_conf"),
            "db_vs_expanded_full": _micro_by_kind("metrics_db_vs_expanded_full"),
        },
        "micro_metrics_by_language": {
            "reducer_vs_db": _micro_by_language("metrics_reducer_vs_db"),
            "db_vs_contract_truth": _micro_by_language("metrics_db_vs_contract"),
            "reducer_vs_contract_truth": _micro_by_language("metrics_reducer_vs_contract"),
            "reducer_vs_enriched_truth": _micro_by_language("metrics_reducer_vs_enriched_truth"),
            "db_vs_enriched_truth": _micro_by_language("metrics_db_vs_enriched_truth"),
            "reducer_vs_expanded_high_conf": _micro_by_language("metrics_reducer_vs_expanded_high_conf"),
            "reducer_vs_expanded_full": _micro_by_language("metrics_reducer_vs_expanded_full"),
            "db_vs_expanded_high_conf": _micro_by_language("metrics_db_vs_expanded_high_conf"),
            "db_vs_expanded_full": _micro_by_language("metrics_db_vs_expanded_full"),
        },
        "micro_metrics_by_language_and_kind": {
            "reducer_vs_db": _micro_by_language_and_kind("metrics_reducer_vs_db"),
            "db_vs_contract_truth": _micro_by_language_and_kind("metrics_db_vs_contract"),
            "reducer_vs_contract_truth": _micro_by_language_and_kind("metrics_reducer_vs_contract"),
            "reducer_vs_enriched_truth": _micro_by_language_and_kind("metrics_reducer_vs_enriched_truth"),
            "db_vs_enriched_truth": _micro_by_language_and_kind("metrics_db_vs_enriched_truth"),
            "reducer_vs_expanded_high_conf": _micro_by_language_and_kind("metrics_reducer_vs_expanded_high_conf"),
            "reducer_vs_expanded_full": _micro_by_language_and_kind("metrics_reducer_vs_expanded_full"),
            "db_vs_expanded_high_conf": _micro_by_language_and_kind("metrics_db_vs_expanded_high_conf"),
            "db_vs_expanded_full": _micro_by_language_and_kind("metrics_db_vs_expanded_full"),
        },
        "call_form_recall": {
            "reducer_vs_contract_truth": call_form_reducer_vs_contract,
            "db_vs_contract_truth": _call_form_recall(
                "metrics_db_vs_contract_by_call_form"
            ),
        },
        "edge_type_breakdown_reducer_vs_contract_truth": edge_breakdown_contract,
        "failure_examples_reducer_vs_contract_truth": failure_examples_contract,
        "out_of_contract_breakdown": aggregate_breakdown(out_of_contract_meta),
        "mismatch_attribution_breakdown": attribution_totals,
        "parity_attribution": parity_attribution,
        "independent_totals": {
            "raw_call_edges": raw_call_total,
            "raw_import_edges": raw_import_total,
            "normalized_call_edges": normalized_call_total,
            "normalized_import_edges": normalized_import_total,
            "contract_truth_edges": expected_total,
            "enriched_truth_edges": enriched_truth_total,
            "expanded_high_conf_edges": expanded_high_total,
            "expanded_full_edges": expanded_full_total,
            "excluded_out_of_scope_edges": excluded_out_of_scope_total,
            "included_limitation_edges": included_limitation_total,
            "independent_static_limitation_edges": independent_limitation_total,
            "contract_exclusion_edges": contract_exclusion_total,
        },
        "independent_coverage_by_language": coverage,
        "class_truth_mapping_quality": {
            "class_rows_parse_ok_with_methods": len(class_rows_parse_ok),
            "class_rows_unreliable_mapping": len(class_rows_unreliable),
            "class_rows_scored": len(class_rows_matchable),
            "unreliable_mapping_rate": (
                (len(class_rows_unreliable) / len(class_rows_parse_ok))
                if class_rows_parse_ok
                else 0.0
            ),
        },
        "call_resolution_diagnostics": {
            "repo_totals": call_resolution_diagnostics_summary,
            "by_language_and_kind": call_resolution_diagnostics_by_language_kind,
        },
        "strict_contract_diagnostics": {
            "accepted_by_provenance": strict_contract_accepted,
            "dropped_by_reason": strict_contract_dropped,
            "candidate_count_histogram": strict_contract_candidate_histogram,
            "policy": strict_policy,
            "policy_violations": policy_violations,
        },
        "population_by_language": sampling.population_by_language,
        "population_by_kind": sampling.population_by_kind,
        "strata_counts": sampling.strata_counts,
        "per_node": rows,
        "overview_errors": overview_errors,
        "stability_score": stability_score,
        "stability_hashes": stability_hashes,
        "stability_error": stability_error,
        "quality_gates": {
            "threshold_profile": profile_name,
            "class_truth_nonempty_rate": class_truth_nonempty_rate,
            "class_truth_nonempty_rate_min": thresholds["class_truth_nonempty_rate_min"],
            "class_truth_match_rate": class_truth_match_rate,
            "class_truth_match_rate_min": thresholds["class_truth_match_rate_min"],
            "scoped_call_normalization_ok": scoped_normalization_ok,
            "strict_contract_parity_ok": strict_contract_parity_ok,
            "strict_contract_policy": strict_policy,
            "strict_contract_policy_violations": policy_violations,
            "contract_recall": contract_recall,
            "contract_recall_min": thresholds["contract_recall_min"],
            "overreach_rate": static_overreach_rate,
            "overreach_rate_max": thresholds["overreach_rate_max"],
            "member_call_recall": member_call_recall,
            "member_call_recall_min": thresholds["member_call_recall_min"],
            "member_call_recall_applicable": member_call_recall_applicable,
        },
        "action_priority_board": action_priority_board,
    }

    write_json(reports.json_path, payload)
    write_markdown(reports.md_path, render_summary(payload))
    print(f"Wrote: {reports.json_path}")
    print(f"Wrote: {reports.md_path}")
    return 0
