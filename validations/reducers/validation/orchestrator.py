# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

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
from .out_of_contract import aggregate_breakdown
from .report import render_summary, write_json, write_markdown
from .reducer_queries import get_snapshot_id


REPORT_SCHEMA_VERSION = "2026-02-26"


def _micro(metric_rows: list[dict], metric_key: str) -> dict:
    tp = sum(row[metric_key]["tp"] for row in metric_rows if row.get(metric_key))
    fp = sum(row[metric_key]["fp"] for row in metric_rows if row.get(metric_key))
    fn = sum(row[metric_key]["fn"] for row in metric_rows if row.get(metric_key))
    precision = (tp / (tp + fp)) if (tp + fp) else None
    recall = (tp / (tp + fn)) if (tp + fn) else None
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall}


def _build_report_payload(
    *,
    repo_root: Path,
    rows: list[dict],
    out_of_contract_meta: list[dict],
) -> dict:
    def _passes_q2_gate(tp: int, fp: int, fn: int, target: float) -> bool:
        precision = (tp / (tp + fp)) if (tp + fp) else None
        recall = (tp / (tp + fn)) if (tp + fn) else None
        return bool(
            precision is not None
            and recall is not None
            and float(precision) >= target
            and float(recall) >= target
            and fp == 0
            and fn == 0
        )

    scored_rows_reducer_vs_contract = [
        row for row in rows if row.get("metrics_reducer_vs_contract") is not None
    ]
    scored_rows_reducer_vs_db = [
        row for row in rows if row.get("metrics_reducer_vs_db") is not None
    ]
    reducer_vs_db_micro = _micro(scored_rows_reducer_vs_db, "metrics_reducer_vs_db")
    reducer_vs_contract_micro = _micro(
        scored_rows_reducer_vs_contract, "metrics_reducer_vs_contract"
    )

    strict_precision = reducer_vs_contract_micro.get("precision")
    strict_recall = reducer_vs_contract_micro.get("recall")
    strict_fp = int(reducer_vs_contract_micro.get("fp") or 0)
    strict_fn = int(reducer_vs_contract_micro.get("fn") or 0)
    strict_target = 0.99

    q2_pass = (
        strict_precision is not None
        and strict_recall is not None
        and float(strict_precision) >= strict_target
        and float(strict_recall) >= strict_target
        and strict_fp == 0
        and strict_fn == 0
    )

    q1_pass = bool(
        reducer_vs_db_micro.get("fp") == 0 and reducer_vs_db_micro.get("fn") == 0
    )
    q1_mismatch_nodes = sum(
        1
        for row in scored_rows_reducer_vs_db
        if int((row.get("metrics_reducer_vs_db") or {}).get("fp") or 0) > 0
        or int((row.get("metrics_reducer_vs_db") or {}).get("fn") or 0) > 0
    )
    reducer_output_edges = int(reducer_vs_db_micro.get("tp") or 0)
    reducer_output_edges_by_language: dict[str, int] = {}
    for row in scored_rows_reducer_vs_db:
        language = str(row.get("language") or "unknown")
        reducer_output_edges_by_language[language] = (
            reducer_output_edges_by_language.get(language, 0)
            + int((row.get("metrics_reducer_vs_db") or {}).get("tp") or 0)
        )

    contract_truth_edges = sum(len(row.get("contract_truth_edges") or []) for row in rows)
    out_of_contract_total = len(out_of_contract_meta)
    breakdown = aggregate_breakdown(out_of_contract_meta)

    by_reason: dict[str, int] = {}
    by_edge_type: dict[str, int] = {}
    by_semantic_type: dict[str, int] = {}
    by_entity_kind: dict[str, int] = {}
    by_language: dict[str, int] = {}
    by_language_semantic: dict[str, dict[str, int]] = {}
    for key, value in breakdown.items():
        edge_type, _language, reason = key.split("::", 2)
        by_reason[reason] = by_reason.get(reason, 0) + int(value)
        by_edge_type[edge_type] = by_edge_type.get(edge_type, 0) + int(value)
    for record in out_of_contract_meta:
        language = str(record.get("language") or "unknown")
        semantic_type = str(record.get("semantic_type") or "unknown")
        entity_kind = str(record.get("entity_kind") or "unknown")
        by_language[language] = by_language.get(language, 0) + 1
        by_language_semantic.setdefault(language, {})[semantic_type] = (
            by_language_semantic.setdefault(language, {}).get(semantic_type, 0) + 1
        )
        by_semantic_type[semantic_type] = by_semantic_type.get(semantic_type, 0) + 1
        by_entity_kind[entity_kind] = by_entity_kind.get(entity_kind, 0) + 1

    by_reason_percent = {
        reason: ((count / out_of_contract_total) * 100.0) if out_of_contract_total else 0.0
        for reason, count in sorted(by_reason.items())
    }
    by_semantic_type_percent = {
        semantic_type: ((count / out_of_contract_total) * 100.0) if out_of_contract_total else 0.0
        for semantic_type, count in sorted(by_semantic_type.items())
    }
    out_of_contract_uplift = (
        (out_of_contract_total / contract_truth_edges) if contract_truth_edges else None
    )
    out_of_contract_vs_reducer_output = (
        ((out_of_contract_total / reducer_output_edges) * 100.0)
        if reducer_output_edges
        else None
    )
    out_of_contract_vs_reducer_output_by_language: dict[str, float | None] = {}
    by_language_semantic_percent: dict[str, dict[str, float]] = {}
    for language, count in sorted(by_language.items()):
        base = int(reducer_output_edges_by_language.get(language) or 0)
        out_of_contract_vs_reducer_output_by_language[language] = (
            ((count / base) * 100.0) if base else None
        )
        per_type = by_language_semantic.get(language) or {}
        by_language_semantic_percent[language] = {
            semantic: ((value / count) * 100.0) if count else 0.0
            for semantic, value in sorted(per_type.items())
        }

    q2_by_language_raw: dict[str, dict[str, float | int | bool | None]] = {}
    for row in scored_rows_reducer_vs_contract:
        language = str(row.get("language") or "unknown")
        metrics = row.get("metrics_reducer_vs_contract") or {}
        bucket = q2_by_language_raw.setdefault(
            language,
            {"tp": 0, "fp": 0, "fn": 0},
        )
        bucket["tp"] = int(bucket["tp"]) + int(metrics.get("tp") or 0)
        bucket["fp"] = int(bucket["fp"]) + int(metrics.get("fp") or 0)
        bucket["fn"] = int(bucket["fn"]) + int(metrics.get("fn") or 0)
    q2_by_language: dict[str, dict[str, float | int | bool | None]] = {}
    for language, bucket in sorted(q2_by_language_raw.items()):
        tp = int(bucket["tp"])
        fp = int(bucket["fp"])
        fn = int(bucket["fn"])
        precision = (tp / (tp + fp)) if (tp + fp) else None
        recall = (tp / (tp + fn)) if (tp + fn) else None
        q2_by_language[language] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "pass": _passes_q2_gate(tp, fp, fn, strict_target),
        }
    q2_language_pass = all(
        bool(bucket.get("pass")) for bucket in q2_by_language.values()
    ) if q2_by_language else False

    invariants = {
        "passed": bool(q1_pass and q2_pass),
        "hard_passed": bool(q1_pass and q2_pass),
        "q1_reducer_vs_db_exact": q1_pass,
        "q2_reducer_vs_contract_near_100": q2_pass,
        "q2_per_language_near_100": q2_language_pass,
        "q3_descriptive_only": True,
    }
    quality_gates = {
        "q2_target": strict_target,
        "q2_precision": strict_precision,
        "q2_recall": strict_recall,
    }

    compact_rows: list[dict] = []
    for row in rows:
        compact_rows.append(
            {
                "entity": row["entity"],
                "language": row["language"],
                "kind": row["kind"],
                "file_path": row["file_path"],
                "module_qualified_name": row["module_qualified_name"],
                "metrics_reducer_vs_db": row.get("metrics_reducer_vs_db"),
                "metrics_reducer_vs_contract": row.get("metrics_reducer_vs_contract"),
                "metrics_db_vs_contract": row.get("metrics_db_vs_contract"),
            }
        )

    summary = [
        f"repo={repo_name_prefix(repo_root)}",
        f"sampled_nodes={len(rows)}",
        f"q1_reducer_vs_db_exact={q1_pass}",
        f"q2_reducer_vs_contract_near_100={q2_pass}",
        f"q3_out_of_contract_total={out_of_contract_total}",
    ]

    return {
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
                "tp": reducer_vs_db_micro.get("tp"),
                "fp": reducer_vs_db_micro.get("fp"),
                "fn": reducer_vs_db_micro.get("fn"),
                "mismatch_nodes": q1_mismatch_nodes,
            },
            "q2": {
                "title": "reducers vs independent within static contract",
                "pass": q2_pass,
                "target": strict_target,
                "precision": strict_precision,
                "recall": strict_recall,
                "fp": strict_fp,
                "fn": strict_fn,
                "contract_truth_edges": contract_truth_edges,
                "by_language": q2_by_language,
            },
            "q3": {
                "title": "beyond static contract envelope",
                "descriptive_only": True,
                "total_edges": out_of_contract_total,
                "uplift_vs_contract_truth": out_of_contract_uplift,
                "additional_vs_reducer_output": out_of_contract_vs_reducer_output,
                "by_reason": dict(sorted(by_reason.items())),
                "by_reason_percent": by_reason_percent,
                "by_edge_type": dict(sorted(by_edge_type.items())),
                "by_semantic_type": dict(sorted(by_semantic_type.items())),
                "by_semantic_type_percent": by_semantic_type_percent,
                "by_entity_kind": dict(sorted(by_entity_kind.items())),
                "by_language_total": dict(sorted(by_language.items())),
                "additional_vs_reducer_output_by_language": out_of_contract_vs_reducer_output_by_language,
                "by_language_semantic_type_percent": by_language_semantic_percent,
            },
        },
    }


def run_validation(
    *,
    repo_root: Path,
    nodes: int,
    seed: int,
) -> int:
    repo_root = repo_root.resolve()
    reports = config.report_paths(repo_root)

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

    payload = _build_report_payload(
        repo_root=repo_root,
        rows=rows,
        out_of_contract_meta=out_of_contract_meta,
    )

    write_json(reports.json_path, payload)
    write_markdown(reports.md_path, render_summary(payload))
    print(f"Wrote: {reports.json_path}")
    print(f"Wrote: {reports.md_path}")
    return 0
