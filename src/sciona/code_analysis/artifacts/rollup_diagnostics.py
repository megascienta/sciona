# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Diagnostics helpers for artifact call rollups."""

from __future__ import annotations

from collections import Counter
from typing import cast

from ..tools.call_extraction import CallExtractionRecord


def ensure_rollup_diagnostics(diagnostics: dict[str, object] | None) -> dict[str, object]:
    if diagnostics is None:
        return {}
    diagnostics.setdefault("version", 1)
    diagnostics.setdefault("by_caller", {})
    totals = diagnostics.setdefault(
        "totals",
        {
            "identifiers_total": 0,
            "accepted_identifiers": 0,
            "dropped_identifiers": 0,
            "accepted_by_provenance": {},
            "dropped_by_reason": {},
            "candidate_count_histogram": {},
            "record_drops": {},
            "assembler_accepted_artifact_dropped": 0,
        },
    )
    return cast(dict[str, object], totals)


def ensure_caller_diagnostics(
    diagnostics: dict[str, object] | None,
    record: CallExtractionRecord,
) -> dict[str, object]:
    if diagnostics is None:
        return {}
    by_caller = cast(dict[str, dict[str, object]], diagnostics.setdefault("by_caller", {}))
    entry = by_caller.setdefault(
        record.caller_structural_id,
        {
            "caller_qualified_name": record.caller_qualified_name,
            "caller_node_type": record.caller_node_type,
            "identifiers_total": 0,
            "accepted_identifiers": 0,
            "dropped_identifiers": 0,
            "accepted_by_provenance": {},
            "dropped_by_reason": {},
            "candidate_count_histogram": {},
            "record_drops": {},
            "assembler_accepted_artifact_dropped": 0,
        },
    )
    return entry


def merge_resolution_stats(
    caller_diag: dict[str, object],
    totals_diag: dict[str, object],
    stats: dict[str, object],
) -> None:
    identifiers_total = int(stats.get("identifiers_total", 0))
    accepted = sum(cast(Counter[str], stats["accepted_by_provenance"]).values())
    dropped = sum(cast(Counter[str], stats["dropped_by_reason"]).values())
    _inc_scalar(caller_diag, "identifiers_total", identifiers_total)
    _inc_scalar(caller_diag, "accepted_identifiers", accepted)
    _inc_scalar(caller_diag, "dropped_identifiers", dropped)
    _inc_scalar(totals_diag, "identifiers_total", identifiers_total)
    _inc_scalar(totals_diag, "accepted_identifiers", accepted)
    _inc_scalar(totals_diag, "dropped_identifiers", dropped)
    _merge_counter_map(
        caller_diag, "accepted_by_provenance", stats["accepted_by_provenance"]
    )
    _merge_counter_map(caller_diag, "dropped_by_reason", stats["dropped_by_reason"])
    _merge_counter_map(
        caller_diag, "candidate_count_histogram", stats["candidate_count_histogram"]
    )
    _merge_counter_map(
        totals_diag, "accepted_by_provenance", stats["accepted_by_provenance"]
    )
    _merge_counter_map(totals_diag, "dropped_by_reason", stats["dropped_by_reason"])
    _merge_counter_map(
        totals_diag, "candidate_count_histogram", stats["candidate_count_histogram"]
    )


def record_resolution_drop(
    caller_diag: dict[str, object],
    totals_diag: dict[str, object],
    *,
    reason: str,
) -> None:
    if caller_diag:
        _inc_map(caller_diag, "record_drops", reason)
        _inc_scalar(caller_diag, "assembler_accepted_artifact_dropped", 1)
    if totals_diag:
        _inc_map(totals_diag, "record_drops", reason)
        _inc_scalar(totals_diag, "assembler_accepted_artifact_dropped", 1)


def _merge_counter_map(
    target: dict[str, object],
    key: str,
    counter_values: object,
) -> None:
    if not target:
        return
    target_map = cast(dict[str, int], target.setdefault(key, {}))
    for bucket, count in cast(Counter[object], counter_values).items():
        if not count:
            continue
        bucket_key = str(bucket)
        target_map[bucket_key] = int(target_map.get(bucket_key, 0)) + int(count)


def _inc_scalar(target: dict[str, object], key: str, amount: int) -> None:
    if not target or not amount:
        return
    target[key] = int(target.get(key, 0)) + amount


def _inc_map(target: dict[str, object], key: str, bucket: str) -> None:
    if not target:
        return
    values = cast(dict[str, int], target.setdefault(key, {}))
    values[bucket] = int(values.get(bucket, 0)) + 1
