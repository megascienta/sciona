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
from sciona.runtime import packaging as runtime_packaging
import yaml

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from experiments.reducers.validation import config
from experiments.reducers.validation.independent.python_ast import parse_python_files
from experiments.reducers.validation.independent.ts_node import parse_typescript_files
from experiments.reducers.validation.independent.java_runner import parse_java_files
from experiments.reducers.validation.independent.shared import EdgeRecord, FileParseResult
from experiments.reducers.validation.independent.normalize import normalize_file_edges
from experiments.reducers.validation.metrics import compute_metrics, compare_edge_sets
from experiments.reducers.validation.report import render_summary, write_json, write_markdown
from experiments.reducers.validation.sampling import build_entities_from_structural_index, sample_entities
from experiments.reducers.validation.call_contract import (
    build_call_resolution_context,
)
from experiments.reducers.validation.ground_truth import (
    build_module_imports_by_prefix,
    edge_records_from_ground_truth,
)
from experiments.reducers.validation.out_of_contract import aggregate_breakdown
from experiments.reducers.validation.db_adapter import (
    graph_edge_targets_for_ids,
    graph_edges_for_ids,
    node_lookup,
    open_artifact_db,
    resolve_node_instance,
    resolve_module_structural_ids,
)
from experiments.reducers.validation.sciona_adapter import (
    get_callsite_index_payload,
    get_dependency_edges_payload,
    get_snapshot_id,
    get_structural_index_hash,
    get_structural_index_payload,
    get_class_overview,
    get_module_overview_payload,
    open_core_db,
)
from sciona.data_storage.artifact_db import read_status as artifact_read_status
from sciona.pipelines.progress import make_progress_factory


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


def _enrich_entities_with_db(entities, conn, snapshot_id) -> None:
    for entity in entities:
        resolved = resolve_node_instance(conn, snapshot_id, entity.qualified_name, entity.kind)
        if not resolved:
            continue
        resolved_path = resolved.get("file_path")
        if resolved_path:
            entity.file_path = resolved_path
        resolved_start = resolved.get("start_line")
        if resolved_start is not None:
            entity.start_line = resolved_start
        resolved_end = resolved.get("end_line")
        if resolved_end is not None:
            entity.end_line = resolved_end
        resolved_lang = resolved.get("language")
        if resolved_lang:
            entity.language = resolved_lang


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


def _load_contract_spec(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("contract spec must be a mapping")
    return data


def _build_import_targets(core_conn, snapshot_id: str) -> dict[str, set[str]]:
    rows = core_conn.execute(
        """
        SELECT src_structural_id, dst_structural_id
        FROM edges
        WHERE snapshot_id = ?
          AND edge_type = 'IMPORTS_DECLARED'
        """,
        (snapshot_id,),
    ).fetchall()
    node_ids = {row["src_structural_id"] for row in rows} | {
        row["dst_structural_id"] for row in rows
    }
    lookup = node_lookup(core_conn, snapshot_id, node_ids)
    targets: dict[str, set[str]] = {}
    for row in rows:
        src_name = lookup.get(row["src_structural_id"], "")
        dst_name = lookup.get(row["dst_structural_id"], "")
        if not src_name or not dst_name:
            continue
        targets.setdefault(src_name, set()).add(dst_name)
    return targets


def _get_file_module_map(entities, conn, snapshot_id) -> Tuple[Dict[str, dict], Dict[str, str]]:
    mapping: Dict[str, dict] = {}
    errors: Dict[str, str] = {}
    for entity in entities:
        file_path = entity.file_path
        module_qname = entity.module_qualified_name or _module_qname_from_entity(entity)
        if not file_path:
            resolved = resolve_node_instance(conn, snapshot_id, entity.qualified_name, entity.kind)
            if resolved and resolved.get("file_path"):
                file_path = resolved.get("file_path")
        if not file_path:
            errors[entity.qualified_name] = "missing file_path"
            continue
        mapping[file_path] = {
            "file_path": file_path,
            "module_qualified_name": module_qname,
            "language": entity.language,
        }
    return mapping, errors


def _build_parse_file_map(
    sampled,
    file_map: Dict[str, dict],
    structural_index: dict,
) -> Dict[str, dict]:
    parse_map = dict(file_map)
    entries = structural_index.get("files", {}).get("entries", []) or []
    module_entries = [
        entry for entry in entries if entry.get("path") and entry.get("module_qualified_name")
    ]
    for entity in sampled:
        if entity.kind != "module":
            continue
        prefix = entity.qualified_name
        for entry in module_entries:
            module_name = entry.get("module_qualified_name")
            if not module_name:
                continue
            if module_name == prefix or module_name.startswith(f"{prefix}."):
                path = entry.get("path")
                if not path:
                    continue
                parse_map.setdefault(
                    path,
                    {
                        "file_path": path,
                        "module_qualified_name": module_name,
                        "language": entry.get("language") or entity.language,
                    },
                )
    return parse_map


def _parse_independent(
    repo_root: Path,
    file_entries: Dict[str, dict],
    progress_factory=None,
) -> Dict[str, FileParseResult]:
    by_language: Dict[str, List[dict]] = {}
    for entry in file_entries.values():
        by_language.setdefault(entry["language"], []).append(entry)

    parsers = {
        "python": parse_python_files,
        "typescript": parse_typescript_files,
        "java": parse_java_files,
    }

    results: Dict[str, FileParseResult] = {}
    for language, entries in by_language.items():
        parser = parsers.get(language)
        if not parser:
            continue
        progress = None
        if progress_factory:
            progress = progress_factory(f"Parsing {language}", len(entries))
        for output in parser(repo_root, entries):
            results[output.file_path] = output
            if progress:
                progress.advance(1)
        if progress:
            progress.close()

    return results


def _collect_reducer_outputs(
    entity,
    conn,
    repo_root,
    snapshot_id,
    module_overviews: Dict[str, dict],
) -> Tuple[Dict[str, object], List[EdgeRecord]]:
    payloads: Dict[str, object] = {}
    edges: List[EdgeRecord] = []
    if entity.kind == "module":
        dep_payload = get_dependency_edges_payload(
            snapshot_id,
            conn,
            repo_root,
            entity.qualified_name,
        )
        payloads["dependency_edges"] = dep_payload
        if entity.qualified_name in module_overviews:
            payloads["module_overview"] = module_overviews[entity.qualified_name]
        for edge in dep_payload.get("edges", []) or []:
            edges.append(_edge_record_from_import(edge))
        return payloads, edges

    if entity.kind == "class":
        class_id = entity.structural_id or entity.qualified_name
        class_payload = get_class_overview(snapshot_id, conn, repo_root, class_id)
        payloads["class_overview"] = class_payload
        method_payloads = []
        for method in class_payload.get("methods", []) or []:
            method_qname = method.get("qualified_name")
            if not method_qname:
                continue
            call_payload = get_callsite_index_payload(
                snapshot_id,
                conn,
                repo_root,
                method_id=method_qname,
            )
            method_payloads.append(call_payload)
            for edge in call_payload.get("edges", []) or []:
                edges.append(_edge_record_from_call(edge, method_qname))
        payloads["callsite_index"] = method_payloads
        return payloads, edges

    if entity.kind == "function":
        call_payload = get_callsite_index_payload(
            snapshot_id,
            conn,
            repo_root,
            function_id=entity.qualified_name,
        )
        payloads["callsite_index"] = call_payload
        for edge in call_payload.get("edges", []) or []:
            edges.append(_edge_record_from_call(edge, entity.qualified_name))
        return payloads, edges

    if entity.kind == "method":
        call_payload = get_callsite_index_payload(
            snapshot_id,
            conn,
            repo_root,
            method_id=entity.qualified_name,
        )
        payloads["callsite_index"] = call_payload
        for edge in call_payload.get("edges", []) or []:
            edges.append(_edge_record_from_call(edge, entity.qualified_name))
        return payloads, edges

    return payloads, edges


def _collect_db_outputs(
    entity,
    core_conn,
    artifact_conn,
    snapshot_id,
) -> Tuple[Dict[str, object], List[EdgeRecord], str | None]:
    payloads: Dict[str, object] = {}
    edges: List[EdgeRecord] = []
    error = None
    try:
        if artifact_conn is None:
            raise RuntimeError("artifact db not available")
        if not artifact_read_status.rebuild_consistent_for_snapshot(
            artifact_conn, snapshot_id=snapshot_id
        ):
            raise RuntimeError("artifact graph not consistent for snapshot")

        if entity.kind == "module":
            module_ids = resolve_module_structural_ids(core_conn, snapshot_id, entity.qualified_name)
            if not module_ids:
                raise RuntimeError("module structural_id not found")
            payloads["module_structural_ids"] = module_ids
            edges = graph_edges_for_ids(
                artifact_conn,
                core_conn,
                snapshot_id,
                module_ids,
                ["IMPORTS_DECLARED"],
            )
            payloads["import_edges"] = [asdict(edge) for edge in edges]
            return payloads, edges, None

        if entity.kind == "class":
            resolved = resolve_node_instance(core_conn, snapshot_id, entity.qualified_name, "class")
            if not resolved or not resolved.get("structural_id"):
                raise RuntimeError("class structural_id not found")
            class_id = resolved["structural_id"]
            payloads["class_structural_id"] = class_id
            method_ids = graph_edge_targets_for_ids(
                artifact_conn,
                [class_id],
                "DEFINES_METHOD",
            )
            payloads["method_structural_ids"] = method_ids
            if method_ids:
                edges = graph_edges_for_ids(
                    artifact_conn,
                    core_conn,
                    snapshot_id,
                    method_ids,
                    ["CALLS"],
                )
            payloads["call_edges"] = [asdict(edge) for edge in edges]
            return payloads, edges, None

        if entity.kind in {"function", "method"}:
            resolved = resolve_node_instance(core_conn, snapshot_id, entity.qualified_name, entity.kind)
            if not resolved or not resolved.get("structural_id"):
                raise RuntimeError("callable structural_id not found")
            call_id = resolved["structural_id"]
            payloads["callable_structural_id"] = call_id
            edges = graph_edges_for_ids(
                artifact_conn,
                core_conn,
                snapshot_id,
                [call_id],
                ["CALLS"],
            )
            payloads["call_edges"] = [asdict(edge) for edge in edges]
            return payloads, edges, None
    except Exception as exc:
        error = str(exc)

    return payloads, edges, error


def _aggregate_group_metrics(rows: List[dict], metric_key: str) -> Dict[str, dict]:
    groups: Dict[str, List[dict]] = {}
    for row in rows:
        key = f"{row['language']}::{row['kind']}"
        groups.setdefault(key, []).append(row)

    metrics: Dict[str, dict] = {}
    for key, entries in groups.items():
        precision_values = [
            r[metric_key]["in_contract_precision"]
            for r in entries
            if r.get(metric_key) and r[metric_key]["in_contract_precision"] is not None
        ]
        recall_values = [
            r[metric_key]["in_contract_recall"]
            for r in entries
            if r.get(metric_key) and r[metric_key]["in_contract_recall"] is not None
        ]
        precision = sum(precision_values) / len(precision_values) if precision_values else None
        recall = sum(recall_values) / len(recall_values) if recall_values else None
        metrics[key] = {"precision": precision, "recall": recall}
    return metrics


def _edge_type_breakdown(rows: List[dict], metric_key: str) -> Dict[str, dict]:
    breakdown: Dict[str, dict] = {
        "calls": {"tp": 0, "fp": 0, "fn": 0},
        "imports": {"tp": 0, "fp": 0, "fn": 0},
    }
    for row in rows:
        if not row.get(metric_key):
            continue
        edge_type = "imports" if row["kind"] == "module" else "calls"
        breakdown[edge_type]["tp"] += row[metric_key]["tp"]
        breakdown[edge_type]["fp"] += row[metric_key]["fp"]
        breakdown[edge_type]["fn"] += row[metric_key]["fn"]
    return breakdown


def _failure_examples(rows: List[dict], metric_key: str, limit: int = 10) -> List[dict]:
    failures = sorted(
        [r for r in rows if r.get(metric_key) and r[metric_key]["in_contract_recall"] is not None],
        key=lambda r: r[metric_key]["in_contract_recall"],
    )
    examples: List[dict] = []
    for entry in failures[:limit]:
        examples.append(
            {
                "node": entry["entity"],
                "issue": f"recall={entry[metric_key]['in_contract_recall']}",
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
    metric_key: str,
) -> dict:
    precision_values = [
        r[metric_key]["in_contract_precision"]
        for r in rows
        if r.get(metric_key) and r[metric_key]["in_contract_precision"] is not None
    ]
    recall_values = [
        r[metric_key]["in_contract_recall"]
        for r in rows
        if r.get(metric_key) and r[metric_key]["in_contract_recall"] is not None
    ]
    precision_mean = sum(precision_values) / len(precision_values) if precision_values else None
    recall_mean = sum(recall_values) / len(recall_values) if recall_values else None

    misses_out_of_contract = sum(
        r[metric_key]["out_of_contract_missing_count"]
        for r in rows
        if r.get(metric_key)
    )
    misses_in_contract = sum(
        r[metric_key]["fn"]
        for r in rows
        if r.get(metric_key)
    )
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


def _aggregate_equivalence(
    rows: List[dict],
    scored_nodes: int,
    total_nodes: int,
    empty_mismatch_count: int,
) -> dict:
    precision_values = [
        r["metrics_db_equivalence"]["in_contract_precision"]
        for r in rows
        if r.get("metrics_db_equivalence")
        and r["metrics_db_equivalence"]["in_contract_precision"] is not None
    ]
    recall_values = [
        r["metrics_db_equivalence"]["in_contract_recall"]
        for r in rows
        if r.get("metrics_db_equivalence")
        and r["metrics_db_equivalence"]["in_contract_recall"] is not None
    ]
    precision_mean = sum(precision_values) / len(precision_values) if precision_values else None
    recall_mean = sum(recall_values) / len(recall_values) if recall_values else None
    coverage_node_rate = (scored_nodes / total_nodes) if total_nodes else None
    return {
        "precision_mean": precision_mean,
        "recall_mean": recall_mean,
        "coverage_node_rate": coverage_node_rate,
        "empty_set_mismatch_count": empty_mismatch_count,
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
    contract_path = Path(__file__).resolve().parent / "validation" / "structural_contract.yaml"
    contract = _load_contract_spec(contract_path)

    with open_core_db(repo_root) as conn:
        snapshot_id = get_snapshot_id(conn)
        with open_artifact_db(repo_root) as artifact_conn:
            structural_index = get_structural_index_payload(snapshot_id, conn, repo_root)
            module_overviews: Dict[str, dict] = {}
            module_entries = structural_index.get("modules", {}).get("entries", []) or []
            progress = make_progress_factory()("Loading module overviews", len(module_entries))
            for entry in module_entries:
                module_name = entry.get("module_qualified_name")
                if not module_name:
                    if progress:
                        progress.advance(1)
                    continue
                module_overviews[module_name] = get_module_overview_payload(
                    snapshot_id,
                    conn,
                    repo_root,
                    module_id=module_name,
                )
                if progress:
                    progress.advance(1)
            if progress:
                progress.close()
            module_names = {
                entry.get("module_qualified_name")
                for entry in structural_index.get("modules", {}).get("entries", [])
                if entry.get("module_qualified_name")
            }
            call_resolution = build_call_resolution_context(module_overviews)
            call_resolution["import_targets"] = _build_import_targets(conn, snapshot_id)
            repo_prefix = repo_name_prefix(repo_root)
            local_packages = set(runtime_packaging.local_package_names(repo_root))

            entities = build_entities_from_structural_index(structural_index, module_overviews)
            _enrich_entities_with_db(entities, conn, snapshot_id)
            sampling = sample_entities(entities, args.nodes, args.seed)
            sampled = sampling.sampled

            file_map, overview_errors = _get_file_module_map(sampled, conn, snapshot_id)
            parse_file_map = _build_parse_file_map(sampled, file_map, structural_index)
            progress_factory = make_progress_factory()
            independent_results = _parse_independent(
                repo_root, parse_file_map, progress_factory=progress_factory
            )

            stability_score = None
            stability_error = None
            try:
                stability_hash_a = get_structural_index_hash(snapshot_id, conn, repo_root)
                stability_hash_b = get_structural_index_hash(snapshot_id, conn, repo_root)
                stability_score = 1.0 if stability_hash_a == stability_hash_b else 0.0
            except Exception as exc:
                stability_error = str(exc)

            normalized_edge_map: Dict[str, Tuple[List[object], List[object]]] = {}
            for file_result in independent_results.values():
                normalized_edge_map[file_result.file_path] = normalize_file_edges(
                    file_result.module_qualified_name,
                    file_result.call_edges,
                    file_result.import_edges,
                )
            module_imports_by_prefix = build_module_imports_by_prefix(
                independent_results, normalized_edge_map
            )

            rows: List[dict] = []
            out_of_contract_meta: List[dict] = []
            total_files = len(independent_results)
            parse_ok_files = sum(
                1 for file_result in independent_results.values() if file_result.parse_ok
            )
            progress = make_progress_factory()("Validating", len(sampled))
            for entity in sampled:
                file_result = independent_results.get(entity.file_path)
                if not file_result:
                    if progress:
                        progress.advance(1)
                    continue
                normalized_calls, normalized_imports = normalized_edge_map.get(
                    entity.file_path, ([], [])
                )
                expected, out_of_contract, out_meta = edge_records_from_ground_truth(
                    file_result,
                    normalized_calls,
                    normalized_imports,
                    module_imports_by_prefix,
                    entity,
                    module_names,
                    call_resolution,
                    contract,
                    repo_root,
                    repo_prefix,
                    local_packages,
                )
                out_of_contract_meta.extend(out_meta)
                reducer_error = None
                db_error = None
                reducer_edges: List[EdgeRecord] = []
                reducer_payloads: Dict[str, object] = {}
                try:
                    reducer_payloads, reducer_edges = _collect_reducer_outputs(
                        entity,
                        conn,
                        repo_root,
                        snapshot_id,
                        module_overviews,
                    )
                except Exception as exc:
                    reducer_error = str(exc)

                db_payloads: Dict[str, object] = {}
                db_edges: List[EdgeRecord] = []
                db_payloads, db_edges, db_error = _collect_db_outputs(
                    entity,
                    conn,
                    artifact_conn,
                    snapshot_id,
                )

                metrics_db_equivalence = None
                metrics_contract = None
                metrics_full = None
                empty_set_mismatch = False
                if not reducer_error and not db_error:
                    metrics_db_equivalence = compare_edge_sets(db_edges, reducer_edges)
                    empty_set_mismatch = bool(db_edges) != bool(reducer_edges)
                if file_result.parse_ok and not reducer_error:
                    metrics_contract = compute_metrics(expected, out_of_contract, reducer_edges)
                    metrics_full = compute_metrics(expected + out_of_contract, [], reducer_edges)
                rows.append(
                    {
                        "entity": entity.qualified_name,
                        "language": entity.language,
                        "kind": entity.kind,
                        "file_path": entity.file_path,
                        "module_qualified_name": entity.module_qualified_name,
                        "metrics_db_equivalence": asdict(metrics_db_equivalence)
                        if metrics_db_equivalence
                        else None,
                        "metrics_contract": asdict(metrics_contract) if metrics_contract else None,
                        "metrics_full": asdict(metrics_full) if metrics_full else None,
                        "db_equivalence_empty_mismatch": empty_set_mismatch,
                        "reducer_payloads": reducer_payloads,
                        "db_payloads": db_payloads,
                        "expected_edges": [asdict(edge) for edge in expected],
                        "out_of_contract_edges": [asdict(edge) for edge in out_of_contract],
                        "ground_truth_parse_ok": file_result.parse_ok,
                        "ground_truth_error": file_result.error,
                        "raw_call_edges_count": len(file_result.call_edges),
                        "raw_import_edges_count": len(file_result.import_edges),
                        "normalized_call_edges_count": len(normalized_calls),
                        "normalized_import_edges_count": len(normalized_imports),
                        "reducer_error": reducer_error,
                        "db_error": db_error,
                    }
                )
                if progress:
                    progress.advance(1)
            if progress:
                progress.close()

    scored_rows_contract = [row for row in rows if row.get("metrics_contract") is not None]
    scored_rows_full = [row for row in rows if row.get("metrics_full") is not None]
    scored_rows_db_equivalence = [
        row for row in rows if row.get("metrics_db_equivalence") is not None
    ]
    empty_set_mismatch_count = sum(
        1 for row in scored_rows_db_equivalence if row.get("db_equivalence_empty_mismatch")
    )
    aggregate_contract = _aggregate(
        scored_rows_contract,
        len(scored_rows_contract),
        len(rows),
        parse_ok_files,
        total_files,
        stability_score or 0.0,
        "metrics_contract",
    )
    aggregate_full = _aggregate(
        scored_rows_full,
        len(scored_rows_full),
        len(rows),
        parse_ok_files,
        total_files,
        stability_score or 0.0,
        "metrics_full",
    )
    aggregate_db_equivalence = _aggregate_equivalence(
        scored_rows_db_equivalence,
        len(scored_rows_db_equivalence),
        len(rows),
        empty_set_mismatch_count,
    )
    group_metrics_contract = _aggregate_group_metrics(scored_rows_contract, "metrics_contract")
    group_metrics_full = _aggregate_group_metrics(scored_rows_full, "metrics_full")
    group_metrics_db_equivalence = _aggregate_group_metrics(
        scored_rows_db_equivalence, "metrics_db_equivalence"
    )
    edge_breakdown_contract = _edge_type_breakdown(scored_rows_contract, "metrics_contract")
    edge_breakdown_full = _edge_type_breakdown(scored_rows_full, "metrics_full")
    edge_breakdown_db_equivalence = _edge_type_breakdown(
        scored_rows_db_equivalence, "metrics_db_equivalence"
    )
    failures_contract = _failure_examples(scored_rows_contract, "metrics_contract")
    failures_full = _failure_examples(scored_rows_full, "metrics_full")
    failures_db_equivalence = _failure_examples(
        scored_rows_db_equivalence, "metrics_db_equivalence"
    )
    threshold_eval = _evaluate_thresholds(aggregate_contract, group_metrics_contract)

    raw_call_total = sum(len(result.call_edges) for result in independent_results.values())
    raw_import_total = sum(len(result.import_edges) for result in independent_results.values())
    normalized_call_total = sum(
        len(edges[0]) for edges in normalized_edge_map.values()
    )
    normalized_import_total = sum(
        len(edges[1]) for edges in normalized_edge_map.values()
    )
    expected_total = sum(len(row["expected_edges"]) for row in rows)
    out_of_contract_total = sum(len(row["out_of_contract_edges"]) for row in rows)

    summary = []
    summary.append(f"repo={repo_name_prefix(repo_root)}")
    summary.append(f"sampled_nodes={len(rows)}")
    if aggregate_db_equivalence.get("precision_mean") is not None:
        summary.append(
            f"db_equivalence_precision_mean={aggregate_db_equivalence['precision_mean']}"
        )
    if aggregate_db_equivalence.get("recall_mean") is not None:
        summary.append(
            f"db_equivalence_recall_mean={aggregate_db_equivalence['recall_mean']}"
        )
    if aggregate_contract.get("in_contract_precision_mean") is not None:
        summary.append(
            f"contract_precision_mean={aggregate_contract['in_contract_precision_mean']}"
        )
    if aggregate_contract.get("in_contract_recall_mean") is not None:
        summary.append(
            f"contract_recall_mean={aggregate_contract['in_contract_recall_mean']}"
        )
    if aggregate_full.get("in_contract_precision_mean") is not None:
        summary.append(
            f"full_precision_mean={aggregate_full['in_contract_precision_mean']}"
        )
    if aggregate_full.get("in_contract_recall_mean") is not None:
        summary.append(f"full_recall_mean={aggregate_full['in_contract_recall_mean']}")
    summary.append(f"thresholds_passed={threshold_eval['passed']}")

    payload = {
        "repo_root": str(repo_root),
        "snapshot_id": snapshot_id,
        "summary": summary,
        "aggregate_db_equivalence": aggregate_db_equivalence,
        "aggregate_contract": aggregate_contract,
        "aggregate_full": aggregate_full,
        "group_metrics_db_equivalence": group_metrics_db_equivalence,
        "group_metrics_contract": group_metrics_contract,
        "group_metrics_full": group_metrics_full,
        "edge_type_breakdown_db_equivalence": edge_breakdown_db_equivalence,
        "edge_type_breakdown_contract": edge_breakdown_contract,
        "edge_type_breakdown_full": edge_breakdown_full,
        "failure_examples_db_equivalence": failures_db_equivalence,
        "failure_examples_contract": failures_contract,
        "failure_examples_full": failures_full,
        "out_of_contract_breakdown": aggregate_breakdown(out_of_contract_meta),
        "independent_totals": {
            "raw_call_edges": raw_call_total,
            "raw_import_edges": raw_import_total,
            "normalized_call_edges": normalized_call_total,
            "normalized_import_edges": normalized_import_total,
            "in_contract_edges": expected_total,
            "out_of_contract_edges": out_of_contract_total,
        },
        "threshold_evaluation_contract": threshold_eval,
        "population_by_language": sampling.population_by_language,
        "population_by_kind": sampling.population_by_kind,
        "strata_counts": sampling.strata_counts,
        "per_node": rows,
        "overview_errors": overview_errors,
        "stability_error": stability_error,
        "thresholds": config.DEFAULT_THRESHOLDS,
    }

    write_json(reports.json_path, payload)
    write_markdown(reports.md_path, render_summary(payload))
    print(f"Wrote: {reports.json_path}")
    print(f"Wrote: {reports.md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
