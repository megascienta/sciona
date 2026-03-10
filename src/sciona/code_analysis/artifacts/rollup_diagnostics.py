# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Diagnostics helpers for artifact call rollups."""

from __future__ import annotations

from typing import cast

from ..analysis_contracts import merge_strict_resolution_stats
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
            "observed_callsites": 0,
            "persisted_callsites": 0,
            "filtered_before_persist": 0,
            "finalized_accepted_callsites": 0,
            "finalized_dropped_callsites": 0,
            "rescue_accepted_callsites": 0,
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
            "observed_callsites": 0,
            "persisted_callsites": 0,
            "filtered_before_persist": 0,
            "finalized_accepted_callsites": 0,
            "finalized_dropped_callsites": 0,
            "rescue_accepted_callsites": 0,
        },
    )
    return entry


def merge_resolution_stats(
    caller_diag: dict[str, object],
    totals_diag: dict[str, object],
    stats: dict[str, object],
) -> None:
    merge_strict_resolution_stats(caller_diag, stats, stringify_counter_keys=True)
    merge_strict_resolution_stats(totals_diag, stats, stringify_counter_keys=True)


def record_resolution_drop(
    caller_diag: dict[str, object],
    totals_diag: dict[str, object],
    *,
    reason: str,
) -> None:
    if caller_diag:
        _inc_map(caller_diag, "record_drops", reason)
    if totals_diag:
        _inc_map(totals_diag, "record_drops", reason)
def record_callsite_flow(
    caller_diag: dict[str, object],
    totals_diag: dict[str, object],
    *,
    observed_callsites: int,
    persisted_callsites: int,
    finalized_accepted_callsites: int,
    finalized_dropped_callsites: int,
    rescue_accepted_callsites: int,
) -> None:
    filtered_before_persist = max(0, observed_callsites - persisted_callsites)
    for target in (caller_diag, totals_diag):
        _inc_scalar(target, "observed_callsites", observed_callsites)
        _inc_scalar(target, "persisted_callsites", persisted_callsites)
        _inc_scalar(target, "filtered_before_persist", filtered_before_persist)
        _inc_scalar(
            target, "finalized_accepted_callsites", finalized_accepted_callsites
        )
        _inc_scalar(target, "finalized_dropped_callsites", finalized_dropped_callsites)
        _inc_scalar(target, "rescue_accepted_callsites", rescue_accepted_callsites)


def _inc_scalar(target: dict[str, object], key: str, amount: int) -> None:
    if not target or not amount:
        return
    target[key] = int(target.get(key, 0)) + amount


def _inc_map(target: dict[str, object], key: str, bucket: str) -> None:
    if not target:
        return
    values = cast(dict[str, int], target.setdefault(key, {}))
    values[bucket] = int(values.get(bucket, 0)) + 1
