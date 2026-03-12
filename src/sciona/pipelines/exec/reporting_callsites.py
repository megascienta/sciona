# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callsite-oriented helpers for snapshot reporting."""

from __future__ import annotations


def count_payload(count: int | None) -> dict[str, object]:
    return {"count": count}


def call_site_funnel_payload(
    *,
    observed_syntactic_callsites: int | None,
    filtered_pre_persist: int | None,
    persisted_callsites: int | None,
    persisted_accepted: int | None,
    persisted_dropped: int | None,
    record_drops: dict[str, int] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "observed_syntactic_callsites": observed_syntactic_callsites,
        "filtered_pre_persist": filtered_pre_persist,
        "persisted_callsites": persisted_callsites,
        "persisted_accepted": persisted_accepted,
        "persisted_dropped": persisted_dropped,
        "record_drops": dict(sorted((record_drops or {}).items())),
        "conservation_ok": None,
    }
    values = (
        observed_syntactic_callsites,
        filtered_pre_persist,
        persisted_callsites,
    )
    if all(value is not None for value in values):
        payload["conservation_ok"] = (
            int(observed_syntactic_callsites or 0)
            == int(filtered_pre_persist or 0) + int(persisted_callsites or 0)
        )
    return payload


def top_items(items: dict[str, int], *, limit: int) -> list[dict[str, object]]:
    ordered = sorted(items.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"name": name, "count": int(count)} for name, count in ordered]


def scope_bucket(file_path: str) -> str:
    if not file_path:
        return "non_tests"
    parts = [segment for segment in file_path.replace("\\", "/").split("/") if segment]
    return "tests" if any(part in {"test", "tests"} for part in parts) else "non_tests"


def scope_count_payload(
    scope_counts: dict[str, int] | None,
) -> dict[str, dict[str, object]] | None:
    if scope_counts is None:
        return None
    payload: dict[str, dict[str, object]] = {}
    for scope_key in ("non_tests", "tests"):
        payload[scope_key] = count_payload(int(scope_counts.get(scope_key, 0)))
    return payload


def scope_call_site_funnel_payload(
    scope_counts: dict[str, dict[str, int]] | None,
) -> dict[str, dict[str, object]] | None:
    if scope_counts is None:
        return None
    payload: dict[str, dict[str, object]] = {}
    for scope_key in ("non_tests", "tests"):
        counts = scope_counts.get(
            scope_key,
            {
                "observed_syntactic_callsites": 0,
                "filtered_pre_persist": 0,
                "persisted_callsites": 0,
                "persisted_accepted": 0,
                "persisted_dropped": 0,
            },
        )
        payload[scope_key] = call_site_funnel_payload(
            observed_syntactic_callsites=int(
                counts.get("observed_syntactic_callsites", 0)
            ),
            filtered_pre_persist=int(counts.get("filtered_pre_persist", 0)),
            persisted_callsites=int(counts.get("persisted_callsites", 0)),
            persisted_accepted=int(counts.get("persisted_accepted", 0)),
            persisted_dropped=int(counts.get("persisted_dropped", 0)),
            record_drops=counts.get("record_drops")
            if isinstance(counts.get("record_drops"), dict)
            else None,
        )
    return payload


def sum_bucket_counts(
    language_buckets: dict[str, dict[str, int]],
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for buckets in language_buckets.values():
        for bucket, count in buckets.items():
            totals[bucket] = totals.get(bucket, 0) + int(count)
    return dict(sorted(totals.items()))


def sum_record_drop_buckets(
    language_buckets: dict[str, dict[str, int]],
) -> dict[str, int]:
    return sum_bucket_counts(language_buckets)


def sum_record_drop_buckets_by_scope(
    language_scope_buckets: dict[str, dict[str, dict[str, int]]],
    *,
    scope_key: str,
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for scope_map in language_scope_buckets.values():
        scope = scope_map.get(scope_key) or {}
        buckets = scope.get("record_drops")
        if not isinstance(buckets, dict):
            continue
        for bucket, count in buckets.items():
            totals[bucket] = totals.get(bucket, 0) + int(count)
    return dict(sorted(totals.items()))


def sum_scope(
    language_scope_totals: dict[str, dict[str, dict[str, int]]],
    *,
    scope_key: str,
    field_names: tuple[str, ...],
) -> dict[str, int]:
    result = {field: 0 for field in field_names}
    for scope_counts in language_scope_totals.values():
        scope = scope_counts.get(scope_key, {})
        for field in field_names:
            result[field] += int(scope.get(field, 0))
    return result


__all__ = [
    "call_site_funnel_payload",
    "count_payload",
    "scope_bucket",
    "scope_call_site_funnel_payload",
    "scope_count_payload",
    "sum_bucket_counts",
    "sum_record_drop_buckets",
    "sum_record_drop_buckets_by_scope",
    "sum_scope",
    "top_items",
]
