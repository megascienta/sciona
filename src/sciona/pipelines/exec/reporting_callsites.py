# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callsite-oriented helpers for snapshot reporting.

Reporting operates on the filtered persisted artifact-layer `call_sites`
working set rather than the full observed syntactic callsite stream.
"""

from __future__ import annotations

from collections import defaultdict


def call_sites_payload(
    eligible: int | None,
    accepted: int | None,
    dropped: int | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "eligible": eligible,
        "accepted": accepted,
        "dropped": dropped,
        "success_rate": None,
    }
    if eligible is None or accepted is None:
        return payload
    if eligible > 0:
        payload["success_rate"] = accepted / eligible
    return payload


def top_items(items: dict[str, int], *, limit: int) -> list[dict[str, object]]:
    ordered = sorted(items.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"name": name, "count": int(count)} for name, count in ordered]


def scope_bucket(file_path: str) -> str:
    if not file_path:
        return "non_tests"
    parts = [segment for segment in file_path.replace("\\", "/").split("/") if segment]
    return "tests" if any(part in {"test", "tests"} for part in parts) else "non_tests"


def scope_call_sites_payload(
    scope_counts: dict[str, dict[str, int]] | None,
) -> dict[str, dict[str, object]] | None:
    if scope_counts is None:
        return None
    payload: dict[str, dict[str, object]] = {}
    for scope_key in ("non_tests", "tests"):
        counts = scope_counts.get(scope_key, {"eligible": 0, "accepted": 0, "dropped": 0})
        payload[scope_key] = call_sites_payload(
            int(counts.get("eligible", 0)),
            int(counts.get("accepted", 0)),
            int(counts.get("dropped", 0)),
        )
    return payload


def drop_classification_bucket(
    *,
    identifier: str,
    drop_reason: str,
    candidate_count: int,
    callee_kind: str,
    known_callable_identifiers: set[str],
) -> str | None:
    if (
        drop_reason == "ambiguous_no_in_scope_candidate"
        and callee_kind == "qualified"
        and candidate_count >= 3
        and "." in identifier
    ):
        if identifier_has_in_repo_callable(
            identifier,
            known_callable_identifiers=known_callable_identifiers,
        ):
            return "in_repo_unresolvable"
        return "external_likely"
    return None


def build_callable_identifier_index(
    caller_metadata: dict[str, dict[str, object]],
) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for meta in caller_metadata.values():
        if str(meta.get("node_type") or "") != "callable":
            continue
        language = str(meta.get("language") or "")
        qualified_name = str(meta.get("qualified_name") or "")
        if not language or not qualified_name:
            continue
        index[language].add(qualified_name)
        terminal = identifier_terminal(qualified_name)
        if terminal:
            index[language].add(terminal)
    return dict(index)


def identifier_has_in_repo_callable(
    identifier: str,
    *,
    known_callable_identifiers: set[str],
) -> bool:
    if not identifier or not known_callable_identifiers:
        return False
    if identifier in known_callable_identifiers:
        return True
    terminal = identifier_terminal(identifier)
    if not terminal:
        return False
    return terminal in known_callable_identifiers


def identifier_terminal(identifier: str) -> str:
    text = identifier.strip()
    if not text:
        return ""
    return text.rsplit(".", 1)[-1].strip()


def sum_bucket_counts(
    language_buckets: dict[str, dict[str, int]],
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for buckets in language_buckets.values():
        for bucket, count in buckets.items():
            totals[bucket] = totals.get(bucket, 0) + int(count)
    return dict(sorted(totals.items()))


def sum_bucket_counts_by_scope(
    language_scope_buckets: dict[str, dict[str, dict[str, int]]],
    *,
    scope_key: str,
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for scope_map in language_scope_buckets.values():
        for bucket, count in (scope_map.get(scope_key) or {}).items():
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
