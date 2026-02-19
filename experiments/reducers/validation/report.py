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

    lines.append("## Aggregate Metrics")
    lines.append("")
    agg = payload.get("aggregate", {})
    for key in [
        "in_contract_precision_mean",
        "in_contract_recall_mean",
        "misses_out_of_contract_rate",
        "coverage_node_rate",
        "coverage_file_rate",
        "stability_score",
    ]:
        if key in agg:
            lines.append(f"- {key}: `{agg[key]}`")
    lines.append("")

    lines.append("## Threshold Evaluation")
    lines.append("")
    threshold_eval = payload.get("threshold_evaluation", {})
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
    for group, stats in payload.get("group_metrics", {}).items():
        lines.append(f"- {group}: precision=`{stats.get('precision')}`, recall=`{stats.get('recall')}`")
    lines.append("")

    lines.append("## Edge Type Breakdown")
    lines.append("")
    for edge_type, stats in payload.get("edge_type_breakdown", {}).items():
        lines.append(
            f"- {edge_type}: tp=`{stats.get('tp')}`, fp=`{stats.get('fp')}`, fn=`{stats.get('fn')}`"
        )
    lines.append("")

    lines.append("## Failure Examples")
    lines.append("")
    failures = payload.get("failure_examples", [])
    if not failures:
        lines.append("- none")
    for item in failures:
        lines.append(f"- {item.get('node')}: {item.get('issue')}")
    return lines
