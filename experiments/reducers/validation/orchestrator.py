# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path
from typing import List

import yaml
from sciona.pipelines.progress import make_progress_factory
from sciona.runtime import packaging as runtime_packaging
from sciona.runtime.paths import repo_name_prefix

from . import config
from .db_adapter import list_nodes_from_artifacts, open_artifact_db
from .evaluation import (
    DbEdgeSource,
    ReducerEdgeSource,
    ResolverCache,
    build_independent_call_resolution,
    build_normalized_edge_maps,
    coverage_by_language,
    evaluate_entities,
    parse_independent_files,
    prepare_parse_map,
    sample_entities_from_db,
)
from .invariants import evaluate_invariants, filter_contract_checks
from .import_contract import resolve_import_contract
from .out_of_contract import aggregate_breakdown
from .report import render_summary, write_json, write_markdown
from .sciona_adapter import get_snapshot_id, open_core_db
from .stability import independent_results_hash
from .stats import edge_type_breakdown, failure_examples, micro


def _load_contract_spec(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("contract spec must be a mapping")
    return data


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


def run_validation(
    *,
    repo_root: Path,
    nodes: int,
    seed: int,
    stability_runs: int,
) -> int:
    repo_root = repo_root.resolve()
    reports = config.report_paths(repo_root)
    contract_path = Path(__file__).resolve().parent / "structural_contract.yaml"
    contract = _load_contract_spec(contract_path)

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

    reducer_full_entities = {row["entity"] for row in scored_rows_reducer_vs_contract}
    db_full_entities = {row["entity"] for row in scored_rows_db_vs_contract}

    reducer_vs_contract_micro = micro(
        scored_rows_reducer_vs_contract, "metrics_reducer_vs_contract"
    )
    db_vs_contract_micro = micro(scored_rows_db_vs_contract, "metrics_db_vs_contract")
    contract_truth_pure_ok, contract_truth_resolved_ok, no_duplicate_contract_edges = (
        filter_contract_checks(rows)
    )
    class_rows_parse_ok = [
        row
        for row in rows
        if row.get("kind") == "class"
        and row.get("ground_truth_parse_ok")
        and row.get("class_has_methods")
    ]
    class_rows_nonempty = [
        row for row in class_rows_parse_ok if not row.get("class_truth_empty_while_parse_ok")
    ]
    class_truth_nonempty_rate = (
        (len(class_rows_nonempty) / len(class_rows_parse_ok))
        if class_rows_parse_ok
        else 1.0
    )

    def _micro_by_kind(metric_key: str) -> dict[str, dict]:
        by_kind: dict[str, dict] = {}
        for kind in ("module", "class", "function", "method"):
            subset = [row for row in rows if row.get("kind") == kind and row.get(metric_key)]
            by_kind[kind] = micro(subset, metric_key) if subset else {}
        return by_kind

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
        typescript_relative_index_contract_ok=_typescript_relative_index_contract_check(contract),
        class_truth_nonempty_rate_ok=(
            class_truth_nonempty_rate >= config.DEFAULT_THRESHOLDS["class_truth_nonempty_rate_min"]
        ),
        scoped_call_normalization_ok=scoped_normalization_ok,
    )

    contract_recall = reducer_vs_contract_micro.get("recall")
    overreach_rate = None
    if reducer_vs_contract_micro["tp"] + reducer_vs_contract_micro["fp"]:
        overreach_rate = reducer_vs_contract_micro["fp"] / (
            reducer_vs_contract_micro["tp"] + reducer_vs_contract_micro["fp"]
        )

    failure_examples_contract = failure_examples(
        scored_rows_reducer_vs_contract, "metrics_reducer_vs_contract"
    )
    edge_breakdown_contract = edge_type_breakdown(
        scored_rows_reducer_vs_contract, "metrics_reducer_vs_contract"
    )

    raw_call_total = sum(len(result.call_edges) for result in independent_results.values())
    raw_import_total = sum(len(result.import_edges) for result in independent_results.values())
    normalized_call_total = sum(
        len(edges[0]) for edges in normalized_edge_map.values()
    )
    normalized_import_total = sum(
        len(edges[1]) for edges in normalized_edge_map.values()
    )
    expected_total = sum(
        len(row.get("contract_truth_edges") or row.get("expected_filtered_edges") or [])
        for row in rows
    )
    out_of_contract_total = sum(
        len(row.get("enrichment_edges") or row.get("out_of_contract_edges") or [])
        for row in rows
    )
    reducer_edge_total = sum(len(row.get("reducer_edges") or []) for row in rows)

    summary = []
    summary.append(f"repo={repo_name_prefix(repo_root)}")
    summary.append(f"sampled_nodes={len(rows)}")
    summary.append(f"invariants_passed={invariants['passed']}")
    summary.append(f"contract_recall={contract_recall}")
    summary.append(f"overreach_rate={overreach_rate}")

    payload = {
        "repo_root": str(repo_root),
        "snapshot_id": snapshot_id,
        "summary": summary,
        "invariants": invariants,
        "core_metrics": {
            "contract_recall": contract_recall,
            "overreach_rate": overreach_rate,
            "overreach_count": reducer_vs_contract_micro["fp"],
            "reducer_edge_total": reducer_edge_total,
        },
        "micro_metrics": {
            "reducer_vs_db": micro(scored_rows_reducer_vs_db, "metrics_reducer_vs_db"),
            "db_vs_contract_truth": db_vs_contract_micro,
            "reducer_vs_contract_truth": reducer_vs_contract_micro,
        },
        "micro_metrics_by_kind": {
            "reducer_vs_db": _micro_by_kind("metrics_reducer_vs_db"),
            "db_vs_contract_truth": _micro_by_kind("metrics_db_vs_contract"),
            "reducer_vs_contract_truth": _micro_by_kind("metrics_reducer_vs_contract"),
        },
        "call_form_recall": {
            "reducer_vs_contract_truth": _call_form_recall(
                "metrics_reducer_vs_contract_by_call_form"
            ),
            "db_vs_contract_truth": _call_form_recall(
                "metrics_db_vs_contract_by_call_form"
            ),
        },
        "edge_type_breakdown_reducer_vs_contract_truth": edge_breakdown_contract,
        "failure_examples_reducer_vs_contract_truth": failure_examples_contract,
        "out_of_contract_breakdown": aggregate_breakdown(out_of_contract_meta),
        "independent_totals": {
            "raw_call_edges": raw_call_total,
            "raw_import_edges": raw_import_total,
            "normalized_call_edges": normalized_call_total,
            "normalized_import_edges": normalized_import_total,
            "contract_truth_edges": expected_total,
            "enrichment_edges": out_of_contract_total,
        },
        "independent_coverage_by_language": coverage,
        "population_by_language": sampling.population_by_language,
        "population_by_kind": sampling.population_by_kind,
        "strata_counts": sampling.strata_counts,
        "per_node": rows,
        "overview_errors": overview_errors,
        "stability_score": stability_score,
        "stability_hashes": stability_hashes,
        "stability_error": stability_error,
        "quality_gates": {
            "class_truth_nonempty_rate": class_truth_nonempty_rate,
            "class_truth_nonempty_rate_min": config.DEFAULT_THRESHOLDS[
                "class_truth_nonempty_rate_min"
            ],
            "scoped_call_normalization_ok": scoped_normalization_ok,
        },
    }

    write_json(reports.json_path, payload)
    write_markdown(reports.md_path, render_summary(payload))
    print(f"Wrote: {reports.json_path}")
    print(f"Wrote: {reports.md_path}")
    return 0
