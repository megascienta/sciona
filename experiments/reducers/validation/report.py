# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path
from typing import List


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

    lines.append("## Hard Invariants")
    lines.append("")
    invariants = payload.get("invariants", {})
    if invariants:
        lines.append(f"- passed: `{invariants.get('passed')}`")
        for key in [
            "gate_reducer_db_exact",
            "gate_aligned_scoring",
            "gate_parse_coverage",
            "gate_filter_subset",
            "gate_filter_resolved",
            "gate_parser_deterministic",
            "gate_no_duplicate_contract_edges",
            "gate_typescript_relative_index_contract",
            "gate_class_truth_nonempty_rate",
            "gate_scoped_call_normalization",
            "gate_equal_full_metrics_when_exact",
        ]:
            lines.append(f"- {key}: `{invariants.get(key)}`")
        for item in invariants.get("failures") or []:
            lines.append(f"- failure: {item}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Core Metrics")
    lines.append("")
    core = payload.get("core_metrics", {})
    if not core:
        lines.append("- none")
    else:
        for key, value in core.items():
            lines.append(f"- {key}: `{value}`")
    lines.append("")

    lines.append("## Determinism")
    lines.append("")
    lines.append(f"- stability_score: `{payload.get('stability_score')}`")
    hashes = payload.get("stability_hashes") or []
    if hashes:
        lines.append(f"- stability_hashes: `{hashes}`")
    if payload.get("stability_error"):
        lines.append(f"- stability_error: `{payload.get('stability_error')}`")
    lines.append("")

    lines.append("## Independent Parser Totals")
    lines.append("")
    independent_totals = payload.get("independent_totals", {})
    for key in [
        "raw_call_edges",
        "raw_import_edges",
        "normalized_call_edges",
        "normalized_import_edges",
        "filtered_in_contract_edges",
        "full_truth_edges",
        "out_of_contract_edges",
    ]:
        if key in independent_totals:
            lines.append(f"- {key}: `{independent_totals[key]}`")

    return lines
