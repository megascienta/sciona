# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_summary(payload: dict) -> List[str]:
    lines: List[str] = []
    lines.append("# SCIONA Reducer Validation Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    for item in payload.get("summary", []):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## DB Equivalence (Reducer vs DB)")
    lines.append("")
    agg_db_eq = payload.get("aggregate_db_equivalence", {})
    for key in [
        "precision_mean",
        "recall_mean",
        "coverage_node_rate",
        "empty_set_mismatch_count",
    ]:
        if key in agg_db_eq:
            lines.append(f"- {key}: `{agg_db_eq[key]}`")
    lines.append("")

    lines.append("## Independent Parser Totals")
    lines.append("")
    independent_totals = payload.get("independent_totals", {})
    for key in [
        "raw_call_edges",
        "raw_import_edges",
        "normalized_call_edges",
        "normalized_import_edges",
        "in_contract_edges",
        "out_of_contract_edges",
    ]:
        if key in independent_totals:
            lines.append(f"- {key}: `{independent_totals[key]}`")
    lines.append("")

    lines.append("## Contract Accuracy (Reducer vs Ground Truth In-Contract)")
    lines.append("")
    agg_contract = payload.get("aggregate_contract", {})
    for key in [
        "in_contract_precision_mean",
        "in_contract_recall_mean",
        "misses_out_of_contract_rate",
        "coverage_node_rate",
        "coverage_file_rate",
        "stability_score",
    ]:
        if key in agg_contract:
            lines.append(f"- {key}: `{agg_contract[key]}`")
    lines.append("")

    lines.append("## Full Accuracy (Reducer vs Full Ground Truth)")
    lines.append("")
    agg_full = payload.get("aggregate_full", {})
    for key in [
        "in_contract_precision_mean",
        "in_contract_recall_mean",
        "misses_out_of_contract_rate",
        "coverage_node_rate",
        "coverage_file_rate",
        "stability_score",
    ]:
        if key in agg_full:
            lines.append(f"- {key}: `{agg_full[key]}`")
    lines.append("")

    lines.append("## Threshold Evaluation (Contract)")
    lines.append("")
    threshold_eval = payload.get("threshold_evaluation_contract", {})
    if threshold_eval:
        lines.append(f"- passed: `{threshold_eval.get('passed')}`")
        failures = threshold_eval.get("failures") or []
        for item in failures:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Group Metrics")
    lines.append("")
    for group, stats in payload.get("group_metrics_db_equivalence", {}).items():
        lines.append(
            f"- db_equivalence {group}: precision=`{stats.get('precision')}`, recall=`{stats.get('recall')}`"
        )
    for group, stats in payload.get("group_metrics_contract", {}).items():
        lines.append(
            f"- contract {group}: precision=`{stats.get('precision')}`, recall=`{stats.get('recall')}`"
        )
    for group, stats in payload.get("group_metrics_full", {}).items():
        lines.append(
            f"- full {group}: precision=`{stats.get('precision')}`, recall=`{stats.get('recall')}`"
        )
    lines.append("")

    lines.append("## Edge Type Breakdown")
    lines.append("")
    for edge_type, stats in payload.get("edge_type_breakdown_db_equivalence", {}).items():
        lines.append(
            f"- db_equivalence {edge_type}: tp=`{stats.get('tp')}`, fp=`{stats.get('fp')}`, fn=`{stats.get('fn')}`"
        )
    for edge_type, stats in payload.get("edge_type_breakdown_contract", {}).items():
        lines.append(
            f"- contract {edge_type}: tp=`{stats.get('tp')}`, fp=`{stats.get('fp')}`, fn=`{stats.get('fn')}`"
        )
    for edge_type, stats in payload.get("edge_type_breakdown_full", {}).items():
        lines.append(
            f"- full {edge_type}: tp=`{stats.get('tp')}`, fp=`{stats.get('fp')}`, fn=`{stats.get('fn')}`"
        )
    lines.append("")

    lines.append("## Failure Examples (DB Equivalence)")
    lines.append("")
    failures_db_eq = payload.get("failure_examples_db_equivalence", [])
    if not failures_db_eq:
        lines.append("- none")
    for item in failures_db_eq:
        lines.append(f"- {item.get('node')}: {item.get('issue')}")
    lines.append("")

    lines.append("## Failure Examples (Contract)")
    lines.append("")
    failures_contract = payload.get("failure_examples_contract", [])
    if not failures_contract:
        lines.append("- none")
    for item in failures_contract:
        lines.append(f"- {item.get('node')}: {item.get('issue')}")
    lines.append("")

    lines.append("## Failure Examples (Full)")
    lines.append("")
    failures_full = payload.get("failure_examples_full", [])
    if not failures_full:
        lines.append("- none")
    for item in failures_full:
        lines.append(f"- {item.get('node')}: {item.get('issue')}")
    return lines
