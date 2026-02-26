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
from .report import render_summary, write_json, write_markdown
from .reducer_queries import get_snapshot_id


REPORT_SCHEMA_VERSION = "2026-02-26"
Q2_FILTERING_SOURCE = "core_only"


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
    return {
        "reference_count": reference_count,
        "candidate_count": candidate_count,
        "intersection_count": intersection_count,
        "missing_count": missing_count,
        "spillover_count": spillover_count,
        "coverage": coverage,
        "spillover_ratio": spillover_ratio,
    }


def _build_report_payload(
    *,
    repo_root: Path,
    rows: list[dict],
    out_of_contract_meta: list[dict],
) -> dict:
    def _passes_q2_gate(coverage: float | None, spillover_ratio: float | None, target: float) -> bool:
        return bool(
            coverage is not None
            and float(coverage) >= target
            and spillover_ratio is not None
            and float(spillover_ratio) <= (1.0 - target)
        )

    scored_rows_q2 = [
        row
        for row in rows
        if row.get("set_q2_reducer_vs_independent_contract") is not None
    ]
    scored_rows_q1 = [row for row in rows if row.get("set_q1_reducer_vs_db") is not None]
    q1_agg = _aggregate_set_metrics(scored_rows_q1, "set_q1_reducer_vs_db")
    q2_agg = _aggregate_set_metrics(
        scored_rows_q2, "set_q2_reducer_vs_independent_contract"
    )

    q2_target = 0.99
    q2_pass = _passes_q2_gate(
        q2_agg.get("coverage"),
        q2_agg.get("spillover_ratio"),
        q2_target,
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
    reducer_output_edges = int(q2_agg.get("reference_count") or 0)

    out_of_contract_total = len(out_of_contract_meta)

    by_semantic_type: dict[str, int] = {}
    for record in out_of_contract_meta:
        semantic_type = str(record.get("semantic_type") or "unknown")
        by_semantic_type[semantic_type] = by_semantic_type.get(semantic_type, 0) + 1

    by_semantic_type_percent = {
        semantic_type: ((count / out_of_contract_total) * 100.0) if out_of_contract_total else 0.0
        for semantic_type, count in sorted(by_semantic_type.items())
    }
    out_of_contract_vs_reducer_output = (
        ((out_of_contract_total / reducer_output_edges) * 100.0)
        if reducer_output_edges
        else None
    )

    q2_by_language_raw: dict[str, dict[str, int]] = {}
    for row in scored_rows_q2:
        language = str(row.get("language") or "unknown")
        metrics = row.get("set_q2_reducer_vs_independent_contract") or {}
        bucket = q2_by_language_raw.setdefault(
            language,
            {
                "reference_count": 0,
                "candidate_count": 0,
                "intersection_count": 0,
                "missing_count": 0,
                "spillover_count": 0,
            },
        )
        for key in bucket:
            bucket[key] = int(bucket[key]) + int(metrics.get(key) or 0)
    q2_by_language: dict[str, dict[str, float | int | bool | None]] = {}
    for language, bucket in sorted(q2_by_language_raw.items()):
        reference_count = int(bucket["reference_count"])
        intersection_count = int(bucket["intersection_count"])
        missing_count = int(bucket["missing_count"])
        spillover_count = int(bucket["spillover_count"])
        candidate_count = int(bucket["candidate_count"])
        coverage = (
            (intersection_count / reference_count) if reference_count else None
        )
        spillover_ratio = (
            (spillover_count / reference_count) if reference_count else None
        )
        q2_by_language[language] = {
            "reference_count": reference_count,
            "candidate_count": candidate_count,
            "intersection_count": intersection_count,
            "missing_count": missing_count,
            "spillover_count": spillover_count,
            "coverage": coverage,
            "spillover_ratio": spillover_ratio,
            "pass": _passes_q2_gate(coverage, spillover_ratio, q2_target),
        }
    q2_language_pass = all(
        bool(bucket.get("pass")) for bucket in q2_by_language.values()
    ) if q2_by_language else False

    invariants = {
        "passed": bool(q1_pass and q2_pass),
        "hard_passed": bool(q1_pass and q2_pass),
        "q1_reducer_vs_db_exact": q1_pass,
        "q2_reducer_vs_independent_overlap": q2_pass,
        "q2_per_language_near_100": q2_language_pass,
        "q3_descriptive_only": True,
    }
    quality_gates = {
        "q2_target_coverage": q2_target,
        "q2_target_spillover_max": (1.0 - q2_target),
        "q2_filtering_source": Q2_FILTERING_SOURCE,
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
                "set_q1_reducer_vs_db": row.get("set_q1_reducer_vs_db"),
                "set_q2_reducer_vs_independent_contract": row.get(
                    "set_q2_reducer_vs_independent_contract"
                ),
            }
        )

    summary = [
        f"repo={repo_name_prefix(repo_root)}",
        f"sampled_nodes={len(rows)}",
        f"q1_reducer_vs_db_exact={q1_pass}",
        f"q2_reducer_vs_independent_overlap={q2_pass}",
        f"q3_out_of_contract_total={out_of_contract_total}",
    ]
    mismatch_candidates: list[tuple[int, int, int, str, dict]] = []
    for row in rows:
        metrics = row.get("set_q2_reducer_vs_independent_contract") or {}
        missing_count = int(metrics.get("missing_count") or 0)
        spillover_count = int(metrics.get("spillover_count") or 0)
        total = missing_count + spillover_count
        if total <= 0:
            continue
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
                    "total_mismatch": total,
                },
            )
        )
    mismatch_candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
    top_mismatch_signatures = [item[4] for item in mismatch_candidates[:20]]

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
                "target_coverage": q2_target,
                "target_spillover_max": (1.0 - q2_target),
                "reference_count": q2_agg.get("reference_count"),
                "candidate_count": q2_agg.get("candidate_count"),
                "intersection_count": q2_agg.get("intersection_count"),
                "missing_count": q2_agg.get("missing_count"),
                "spillover_count": q2_agg.get("spillover_count"),
                "coverage": q2_agg.get("coverage"),
                "spillover_ratio": q2_agg.get("spillover_ratio"),
                "by_language": q2_by_language,
                "filtering_source": Q2_FILTERING_SOURCE,
                "top_mismatch_signatures": top_mismatch_signatures,
            },
            "q3": {
                "title": "beyond static contract envelope",
                "descriptive_only": True,
                "total_edges": out_of_contract_total,  # |S3|
                "additional_vs_reducer_output": out_of_contract_vs_reducer_output,
                "by_semantic_type": dict(sorted(by_semantic_type.items())),
                "by_semantic_type_percent": by_semantic_type_percent,
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
