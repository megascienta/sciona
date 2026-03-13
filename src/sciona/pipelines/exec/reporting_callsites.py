# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callsite-oriented helpers for snapshot reporting."""

from __future__ import annotations

PRE_PERSIST_BUCKET_KEYS = (
    "no_in_repo_candidate_terminal",
    "no_in_repo_candidate_qualified",
    "accepted_outside_in_repo",
    "invalid_observation_shape",
)


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


def filtered_pre_persist_buckets_payload(
    buckets: dict[str, int] | None,
) -> dict[str, int]:
    source = buckets or {}
    return {
        key: int(source.get(key, 0))
        for key in PRE_PERSIST_BUCKET_KEYS
    }


def scope_filtered_pre_persist_buckets_payload(
    scope_buckets: dict[str, dict[str, int]] | None,
) -> dict[str, dict[str, int]] | None:
    if scope_buckets is None:
        return None
    payload: dict[str, dict[str, int]] = {}
    for scope_key in ("non_tests", "tests"):
        buckets = scope_buckets.get(scope_key)
        if not isinstance(buckets, dict):
            buckets = {}
        payload[scope_key] = filtered_pre_persist_buckets_payload(buckets)
    return payload


def persisted_callsite_pair_expansion_payload(
    *,
    persisted_callsites: int | None,
    persisted_callsites_with_zero_pairs: int | None,
    persisted_callsites_with_one_pair: int | None,
    persisted_callsites_with_multiple_pairs: int | None,
    pair_count: int | None,
    max_pairs_for_single_persisted_callsite: int | None,
) -> dict[str, object]:
    persisted = int(persisted_callsites or 0) if persisted_callsites is not None else None
    zero = (
        int(persisted_callsites_with_zero_pairs or 0)
        if persisted_callsites_with_zero_pairs is not None
        else None
    )
    one = (
        int(persisted_callsites_with_one_pair or 0)
        if persisted_callsites_with_one_pair is not None
        else None
    )
    multiple = (
        int(persisted_callsites_with_multiple_pairs or 0)
        if persisted_callsites_with_multiple_pairs is not None
        else None
    )
    pairs = int(pair_count or 0) if pair_count is not None else None
    payload: dict[str, object] = {
        "persisted_callsites": persisted,
        "persisted_callsites_with_zero_pairs": zero,
        "persisted_callsites_with_one_pair": one,
        "persisted_callsites_with_multiple_pairs": multiple,
        "pair_expansion_factor": None,
        "multi_pair_share": None,
        "max_pairs_for_single_persisted_callsite": (
            int(max_pairs_for_single_persisted_callsite or 0)
            if max_pairs_for_single_persisted_callsite is not None
            else None
        ),
    }
    if persisted is not None and persisted > 0:
        if pairs is not None:
            payload["pair_expansion_factor"] = pairs / persisted
        if multiple is not None:
            payload["multi_pair_share"] = multiple / persisted
    return payload


def scope_persisted_callsite_pair_expansion_payload(
    scope_counts: dict[str, dict[str, object]] | None,
    *,
    pair_scope_counts: dict[str, int] | None,
) -> dict[str, dict[str, object]] | None:
    if scope_counts is None:
        return None
    payload: dict[str, dict[str, object]] = {}
    for scope_key in ("non_tests", "tests"):
        counts = scope_counts.get(
            scope_key,
            {
                "persisted_callsites": 0,
                "persisted_callsite_pair_expansion": {},
            },
        )
        expansion = counts.get("persisted_callsite_pair_expansion")
        if not isinstance(expansion, dict):
            expansion = counts
        payload[scope_key] = persisted_callsite_pair_expansion_payload(
            persisted_callsites=int(counts.get("persisted_callsites", 0)),
            persisted_callsites_with_zero_pairs=int(
                expansion.get("persisted_callsites_with_zero_pairs", 0)
            ),
            persisted_callsites_with_one_pair=int(
                expansion.get("persisted_callsites_with_one_pair", 0)
            ),
            persisted_callsites_with_multiple_pairs=int(
                expansion.get("persisted_callsites_with_multiple_pairs", 0)
            ),
            pair_count=int((pair_scope_counts or {}).get(scope_key, 0)),
            max_pairs_for_single_persisted_callsite=int(
                expansion.get("max_pairs_for_single_persisted_callsite", 0)
            ),
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
    "persisted_callsite_pair_expansion_payload",
    "scope_bucket",
    "scope_call_site_funnel_payload",
    "scope_count_payload",
    "scope_persisted_callsite_pair_expansion_payload",
    "sum_bucket_counts",
    "sum_record_drop_buckets",
    "sum_record_drop_buckets_by_scope",
    "sum_scope",
    "top_items",
]
