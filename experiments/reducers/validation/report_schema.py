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
    metrics_reducer_vs_db: NotRequired[dict | None]
    metrics_reducer_vs_contract: NotRequired[dict | None]
    metrics_db_vs_contract: NotRequired[dict | None]


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
    for metric_key in (
        "metrics_reducer_vs_db",
        "metrics_reducer_vs_contract",
        "metrics_db_vs_contract",
    ):
        metric = row.get(metric_key)
        if metric is not None and not isinstance(metric, Mapping):
            errors.append(f"per_node[{index}].{metric_key} must be a mapping or null")
    return errors


__all__ = ["ReportPayload", "ReportRow", "validate_report_payload"]
