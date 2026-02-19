#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from sciona.runtime.paths import repo_name_prefix

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from experiments.reducers.validation import config
from experiments.reducers.validation.independent.python_ast import parse_python_file
from experiments.reducers.validation.independent.ts_node import parse_typescript_files
from experiments.reducers.validation.independent.java_runner import parse_java_files
from experiments.reducers.validation.independent.shared import EdgeRecord, FileParseResult
from experiments.reducers.validation.metrics import compute_metrics
from experiments.reducers.validation.report import render_summary, write_json, write_markdown
from experiments.reducers.validation.sampling import load_entities, sample_entities
from experiments.reducers.validation.sciona_adapter import (
    get_call_edges,
    get_class_methods,
    get_dependency_edges,
    get_snapshot_id,
    get_structural_index_hash,
    get_callable_overview,
    get_class_overview,
    get_module_overview,
    open_core_db,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SCIONA reducers against independent parsers.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--nodes", type=int, default=config.DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    return parser.parse_args()


def _module_qname_from_entity(entity) -> str:
    parts = entity.qualified_name.split(".")
    if entity.kind == "module":
        return entity.qualified_name
    if len(parts) > 1:
        return ".".join(parts[:-1])
    return entity.qualified_name


def _edge_record_from_call(edge: dict, fallback_caller: str) -> EdgeRecord:
    caller = edge.get("caller_qualified_name") or fallback_caller
    callee_qname = edge.get("callee_qualified_name")
    callee = edge.get("callee_identifier") or edge.get("callee_name")
    if not callee and callee_qname:
        callee = callee_qname.split(".")[-1]
    return EdgeRecord(caller=caller, callee=callee or "", callee_qname=callee_qname)


def _edge_record_from_import(edge: dict) -> EdgeRecord:
    caller = edge.get("from_module_qualified_name") or ""
    callee = edge.get("to_module_qualified_name") or ""
    return EdgeRecord(caller=caller, callee=callee, callee_qname=callee)


def _edge_records_from_ground_truth(
    file_result: FileParseResult, entity
) -> Tuple[List[EdgeRecord], List[EdgeRecord]]:
    expected: List[EdgeRecord] = []
    out_of_contract: List[EdgeRecord] = []

    if entity.kind == "module":
        for edge in file_result.import_edges:
            record = EdgeRecord(
                caller=file_result.module_qualified_name,
                callee=edge.target_module,
                callee_qname=edge.target_module,
            )
            if edge.dynamic:
                out_of_contract.append(record)
            else:
                expected.append(record)
        return expected, out_of_contract

    if entity.kind == "class":
        prefix = f"{entity.qualified_name}."
        for edge in file_result.call_edges:
            if not edge.caller.startswith(prefix):
                continue
            record = EdgeRecord(edge.caller, edge.callee, edge.callee_qname)
            if edge.dynamic:
                out_of_contract.append(record)
            else:
                expected.append(record)
        return expected, out_of_contract

    for edge in file_result.call_edges:
        if edge.caller != entity.qualified_name:
            continue
        record = EdgeRecord(edge.caller, edge.callee, edge.callee_qname)
        if edge.dynamic:
            out_of_contract.append(record)
        else:
            expected.append(record)
    return expected, out_of_contract


def _get_file_module_map(entities, repo_root, conn, snapshot_id) -> Tuple[Dict[str, dict], Dict[str, str]]:
    mapping: Dict[str, dict] = {}
    errors: Dict[str, str] = {}
    for entity in entities:
        try:
            if entity.kind == "module":
                overview = get_module_overview(snapshot_id, conn, repo_root, entity.qualified_name)
                module_qname = overview.get("module_qualified_name") or entity.qualified_name
                file_path = (overview.get("files") or [entity.file_path])[0]
            elif entity.kind == "class":
                overview = get_class_overview(snapshot_id, conn, repo_root, entity.qualified_name)
                module_qname = overview.get("module_qualified_name") or _module_qname_from_entity(entity)
                file_path = overview.get("file_path") or entity.file_path
            else:
                overview = get_callable_overview(
                    snapshot_id,
                    conn,
                    repo_root,
                    function_id=entity.qualified_name if entity.kind == "function" else None,
                    method_id=entity.qualified_name if entity.kind == "method" else None,
                    callable_id=entity.qualified_name,
                )
                module_qname = overview.get("module_qualified_name") or _module_qname_from_entity(entity)
                file_path = overview.get("file_path") or entity.file_path
        except Exception as exc:
            errors[entity.qualified_name] = str(exc)
            module_qname = _module_qname_from_entity(entity)
            file_path = entity.file_path

        if file_path:
            mapping[file_path] = {
                "file_path": file_path,
                "module_qualified_name": module_qname,
                "language": entity.language,
            }
    return mapping, errors


def _parse_independent(repo_root: Path, file_entries: Dict[str, dict]) -> Dict[str, FileParseResult]:
    python_files = []
    ts_files = []
    java_files = []
    for entry in file_entries.values():
        if entry["language"] == "python":
            python_files.append(entry)
        elif entry["language"] == "typescript":
            ts_files.append(entry)
        elif entry["language"] == "java":
            java_files.append(entry)

    results: Dict[str, FileParseResult] = {}
    for entry in python_files:
        results[entry["file_path"]] = parse_python_file(repo_root, entry["file_path"], entry["module_qualified_name"])

    if ts_files:
        for output in parse_typescript_files(repo_root, ts_files):
            results[output.file_path] = output

    if java_files:
        for output in parse_java_files(repo_root, java_files):
            results[output.file_path] = output

    return results


def _collect_sciona_edges(entity, conn, repo_root, snapshot_id) -> List[EdgeRecord]:
    edges: List[EdgeRecord] = []
    if entity.kind == "module":
        for edge in get_dependency_edges(snapshot_id, conn, repo_root, entity.qualified_name):
            edges.append(_edge_record_from_import(edge))
        return edges

    if entity.kind == "class":
        methods = get_class_methods(snapshot_id, conn, repo_root, entity.qualified_name)
        for method in methods:
            method_qname = method.get("qualified_name")
            if not method_qname:
                continue
            for edge in get_call_edges(
                snapshot_id,
                conn,
                repo_root,
                method_id=method_qname,
            ):
                edges.append(_edge_record_from_call(edge, method_qname))
        return edges

    if entity.kind == "function":
        for edge in get_call_edges(snapshot_id, conn, repo_root, function_id=entity.qualified_name):
            edges.append(_edge_record_from_call(edge, entity.qualified_name))
        return edges

    if entity.kind == "method":
        for edge in get_call_edges(snapshot_id, conn, repo_root, method_id=entity.qualified_name):
            edges.append(_edge_record_from_call(edge, entity.qualified_name))
        return edges

    return edges


def _aggregate_group_metrics(rows: List[dict]) -> Dict[str, dict]:
    groups: Dict[str, List[dict]] = {}
    for row in rows:
        key = f"{row['language']}::{row['kind']}"
        groups.setdefault(key, []).append(row)

    metrics: Dict[str, dict] = {}
    for key, entries in groups.items():
        precision_values = [r["metrics"]["in_contract_precision"] for r in entries if r["metrics"]["in_contract_precision"] is not None]
        recall_values = [r["metrics"]["in_contract_recall"] for r in entries if r["metrics"]["in_contract_recall"] is not None]
        precision = sum(precision_values) / len(precision_values) if precision_values else None
        recall = sum(recall_values) / len(recall_values) if recall_values else None
        metrics[key] = {"precision": precision, "recall": recall}
    return metrics


def _edge_type_breakdown(rows: List[dict]) -> Dict[str, dict]:
    breakdown: Dict[str, dict] = {
        "calls": {"tp": 0, "fp": 0, "fn": 0},
        "imports": {"tp": 0, "fp": 0, "fn": 0},
    }
    for row in rows:
        edge_type = "imports" if row["kind"] == "module" else "calls"
        breakdown[edge_type]["tp"] += row["metrics"]["tp"]
        breakdown[edge_type]["fp"] += row["metrics"]["fp"]
        breakdown[edge_type]["fn"] += row["metrics"]["fn"]
    return breakdown


def _failure_examples(rows: List[dict], limit: int = 10) -> List[dict]:
    failures = sorted(
        [r for r in rows if r["metrics"]["in_contract_recall"] is not None],
        key=lambda r: r["metrics"]["in_contract_recall"],
    )
    examples: List[dict] = []
    for entry in failures[:limit]:
        examples.append(
            {
                "node": entry["entity"],
                "issue": f"recall={entry['metrics']['in_contract_recall']}",
            }
        )
    return examples


def _aggregate(
    rows: List[dict],
    scored_nodes: int,
    total_nodes: int,
    parse_ok_files: int,
    total_files: int,
    stability_score: float,
) -> dict:
    precision_values = [r["metrics"]["in_contract_precision"] for r in rows if r["metrics"]["in_contract_precision"] is not None]
    recall_values = [r["metrics"]["in_contract_recall"] for r in rows if r["metrics"]["in_contract_recall"] is not None]
    precision_mean = sum(precision_values) / len(precision_values) if precision_values else None
    recall_mean = sum(recall_values) / len(recall_values) if recall_values else None

    misses_out_of_contract = sum(r["metrics"]["out_of_contract_missing_count"] for r in rows)
    misses_in_contract = sum(r["metrics"]["fn"] for r in rows)
    denom = misses_out_of_contract + misses_in_contract
    misses_out_rate = (misses_out_of_contract / denom) if denom else None

    coverage_file_rate = parse_ok_files / total_files if total_files else None
    coverage_node_rate = (scored_nodes / total_nodes) if total_nodes else None

    return {
        "in_contract_precision_mean": precision_mean,
        "in_contract_recall_mean": recall_mean,
        "misses_out_of_contract_rate": misses_out_rate,
        "coverage_node_rate": coverage_node_rate,
        "coverage_file_rate": coverage_file_rate,
        "stability_score": stability_score,
    }


def _evaluate_thresholds(aggregate: dict, group_metrics: Dict[str, dict]) -> Dict[str, object]:
    thresholds = config.DEFAULT_THRESHOLDS
    results = {"passed": True, "failures": []}

    def _check(name: str, value: float | None, limit: float, comparator: str) -> None:
        if value is None:
            results["passed"] = False
            results["failures"].append(f"{name} missing")
            return
        if comparator == ">=" and value < limit:
            results["passed"] = False
            results["failures"].append(f"{name} {value} < {limit}")

    _check("precision_mean", aggregate.get("in_contract_precision_mean"), thresholds["precision_mean_min"], ">=")
    _check("recall_mean", aggregate.get("in_contract_recall_mean"), thresholds["recall_mean_min"], ">=")
    _check(
        "misses_out_of_contract_rate",
        aggregate.get("misses_out_of_contract_rate"),
        thresholds["misses_out_of_contract_rate_min"],
        ">=",
    )

    for key, stats in group_metrics.items():
        precision = stats.get("precision")
        recall = stats.get("recall")
        if precision is not None and precision < thresholds["precision_min_by_group"]:
            results["passed"] = False
            results["failures"].append(f"group {key} precision {precision} < {thresholds['precision_min_by_group']}")
        if recall is not None and recall < thresholds["recall_min_by_group"]:
            results["passed"] = False
            results["failures"].append(f"group {key} recall {recall} < {thresholds['recall_min_by_group']}")

    return results


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    reports = config.report_paths(repo_root)

    with open_core_db(repo_root) as conn:
        snapshot_id = get_snapshot_id(conn)
        entities = load_entities(repo_root, repo_root / ".sciona" / "sciona.db")
        sampling = sample_entities(entities, repo_root, args.nodes, args.seed)
        sampled = sampling.sampled

        file_map, overview_errors = _get_file_module_map(sampled, repo_root, conn, snapshot_id)
        independent_results = _parse_independent(repo_root, file_map)

        stability_hash_a = get_structural_index_hash(snapshot_id, conn, repo_root)
        stability_hash_b = get_structural_index_hash(snapshot_id, conn, repo_root)
        stability_score = 1.0 if stability_hash_a == stability_hash_b else 0.0

        rows: List[dict] = []
        parse_ok_files = 0
        total_files = len(independent_results)
        for entity in sampled:
            file_result = independent_results.get(entity.file_path)
            if not file_result:
                continue
            if file_result.parse_ok:
                parse_ok_files += 1
            expected, out_of_contract = _edge_records_from_ground_truth(file_result, entity)
            reducer_error = None
            sciona_edges = []
            try:
                sciona_edges = _collect_sciona_edges(entity, conn, repo_root, snapshot_id)
            except Exception as exc:
                reducer_error = str(exc)
            metrics = None
            if file_result.parse_ok and not reducer_error:
                metrics = compute_metrics(expected, out_of_contract, sciona_edges)
            rows.append(
                {
                    "entity": entity.qualified_name,
                    "language": entity.language,
                    "kind": entity.kind,
                    "file_path": entity.file_path,
                    "metrics": asdict(metrics) if metrics else None,
                    "ground_truth_parse_ok": file_result.parse_ok,
                    "ground_truth_error": file_result.error,
                    "reducer_error": reducer_error,
                }
            )

    scored_rows = [row for row in rows if row["metrics"] is not None]
    aggregate = _aggregate(scored_rows, len(scored_rows), len(rows), parse_ok_files, total_files, stability_score)
    group_metrics = _aggregate_group_metrics(scored_rows)
    edge_breakdown = _edge_type_breakdown(scored_rows)
    failures = _failure_examples(scored_rows)
    threshold_eval = _evaluate_thresholds(aggregate, group_metrics)

    summary = []
    summary.append(f"repo={repo_name_prefix(repo_root)}")
    summary.append(f"sampled_nodes={len(rows)}")
    if aggregate.get("in_contract_precision_mean") is not None:
        summary.append(f"precision_mean={aggregate['in_contract_precision_mean']}")
    if aggregate.get("in_contract_recall_mean") is not None:
        summary.append(f"recall_mean={aggregate['in_contract_recall_mean']}")
    summary.append(f"thresholds_passed={threshold_eval['passed']}")

    payload = {
        "repo_root": str(repo_root),
        "snapshot_id": snapshot_id,
        "summary": summary,
        "aggregate": aggregate,
        "group_metrics": group_metrics,
        "edge_type_breakdown": edge_breakdown,
        "failure_examples": failures,
        "threshold_evaluation": threshold_eval,
        "population_by_language": sampling.population_by_language,
        "population_by_kind": sampling.population_by_kind,
        "strata_counts": sampling.strata_counts,
        "per_node": rows,
        "overview_errors": overview_errors,
        "thresholds": config.DEFAULT_THRESHOLDS,
    }

    write_json(reports.json_path, payload)
    write_markdown(reports.md_path, render_summary(payload))
    print(f"Wrote: {reports.json_path}")
    print(f"Wrote: {reports.md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
