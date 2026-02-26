# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Mapping, NotRequired, Required, TypedDict


class ReportRow(TypedDict, total=False):
    entity: Required[str]
    language: Required[str]
    kind: Required[str]
    file_path: Required[str]
    module_qualified_name: Required[str]
    set_q1_reducer_vs_db: NotRequired[dict | None]
    set_q2_reducer_vs_independent_contract: NotRequired[dict | None]
    basket2_edges: NotRequired[list]
    q2_node_rates: NotRequired[dict | None]
    q3_out_of_contract_rate_percent: NotRequired[float | None]


class ReportPayload(TypedDict, total=False):
    summary: Required[list[str]]
    per_node: Required[list[ReportRow]]
    invariants: Required[dict]
    quality_gates: Required[dict]


_ALLOWED_KINDS = {"module", "class", "function", "method"}


def validate_report_payload(payload: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    for key in ("summary", "per_node", "invariants", "quality_gates"):
        if key not in payload:
            errors.append(f"missing required payload key: {key}")
    summary = payload.get("summary")
    if summary is not None:
        if not isinstance(summary, list) or not all(
            isinstance(item, str) for item in summary
        ):
            errors.append("summary must be a list[str]")
    rows = payload.get("per_node")
    if rows is not None:
        if not isinstance(rows, list):
            errors.append("per_node must be a list")
        else:
            for index, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    errors.append(f"per_node[{index}] must be a mapping")
                    continue
                errors.extend(_validate_row(row, index))
    invariants = payload.get("invariants")
    if invariants is not None and not isinstance(invariants, Mapping):
        errors.append("invariants must be a mapping")
    quality_gates = payload.get("quality_gates")
    if quality_gates is not None and not isinstance(quality_gates, Mapping):
        errors.append("quality_gates must be a mapping")
    return errors


def _validate_row(row: Mapping[str, object], index: int) -> list[str]:
    errors: list[str] = []
    for key in ("entity", "language", "kind", "file_path", "module_qualified_name"):
        value = row.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"per_node[{index}].{key} must be a non-empty string")
    kind = row.get("kind")
    if isinstance(kind, str) and kind not in _ALLOWED_KINDS:
        errors.append(
            f"per_node[{index}].kind must be one of {sorted(_ALLOWED_KINDS)}"
        )
    forbidden_legacy = (
        "metrics_reducer_vs_db",
        "metrics_reducer_vs_contract",
        "metrics_db_vs_contract",
    )
    for legacy_key in forbidden_legacy:
        if legacy_key in row:
            errors.append(f"per_node[{index}].{legacy_key} is not allowed in current schema")
    for metric_key in (
        "set_q1_reducer_vs_db",
        "set_q2_reducer_vs_independent_contract",
        "q2_node_rates",
    ):
        metric = row.get(metric_key)
        if metric is not None and not isinstance(metric, Mapping):
            errors.append(f"per_node[{index}].{metric_key} must be a mapping or null")
    basket2_edges = row.get("basket2_edges")
    if basket2_edges is not None and not isinstance(basket2_edges, list):
        errors.append(f"per_node[{index}].basket2_edges must be a list or null")
    q3_percent = row.get("q3_out_of_contract_rate_percent")
    if q3_percent is not None and not isinstance(q3_percent, (int, float)):
        errors.append(
            f"per_node[{index}].q3_out_of_contract_rate_percent must be numeric or null"
        )
    return errors


__all__ = ["ReportPayload", "ReportRow", "validate_report_payload"]
