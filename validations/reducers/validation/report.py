# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .report_schema import validate_report_payload


def write_json(path: Path, payload: dict) -> None:
    errors = validate_report_payload(payload)
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"report payload validation failed: {joined}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_summary(payload: dict) -> List[str]:
    lines: List[str] = []
    lines.append("# SCIONA Reducer Validation Report")
    lines.append("")
    questions = payload.get("questions") or {}

    q1 = questions.get("q1") or {}
    lines.append("## Q1. Reducers vs DB Correctness")
    lines.append("")
    lines.append(f"- pass: `{q1.get('pass')}`")
    lines.append(f"- exact_required: `{q1.get('exact_required')}`")
    lines.append(
        f"- tp/fp/fn: `{q1.get('tp')}`/`{q1.get('fp')}`/`{q1.get('fn')}`"
    )
    lines.append(f"- mismatch_nodes: `{q1.get('mismatch_nodes')}`")
    lines.append("")

    q2 = questions.get("q2") or {}
    lines.append("## Q2. Reducers vs Independent Within Static Contract")
    lines.append("")
    lines.append(f"- pass: `{q2.get('pass')}`")
    lines.append(f"- target: `{_format_value(q2.get('target'))}`")
    lines.append(
        f"- precision/recall: `{_format_value(q2.get('precision'))}`/`{_format_value(q2.get('recall'))}`"
    )
    lines.append(f"- fp/fn: `{q2.get('fp')}`/`{q2.get('fn')}`")
    lines.append(f"- contract_truth_edges: `{q2.get('contract_truth_edges')}`")
    lines.append("")

    q3 = questions.get("q3") or {}
    lines.append("## Q3. Beyond Static Contract Envelope")
    lines.append("")
    lines.append(
        f"- additional_vs_reducer_output_percent: `{_format_value(q3.get('additional_vs_reducer_output'))}`"
    )
    lines.append(f"- percent_by_type: `{q3.get('by_semantic_type_percent')}`")
    lines.append("")
    return lines
