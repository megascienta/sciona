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


def adjusted_call_sites_payload(
    call_sites: dict[str, object] | None,
    *,
    excluded_external_likely: int,
) -> dict[str, object]:
    eligible = call_sites.get("eligible") if call_sites else None
    accepted = call_sites.get("accepted") if call_sites else None
    adjusted_eligible = None
    success_rate = None
    if isinstance(eligible, int):
        adjusted_eligible = max(eligible - int(excluded_external_likely or 0), 0)
    if isinstance(adjusted_eligible, int) and adjusted_eligible > 0 and isinstance(accepted, int):
        success_rate = accepted / adjusted_eligible
    return {
        "eligible": eligible,
        "accepted": accepted,
        "excluded_external_likely": int(excluded_external_likely or 0),
        "adjusted_eligible": adjusted_eligible,
        "success_rate": success_rate,
    }


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


def scope_adjusted_call_sites_payload(
    scope_payload: dict[str, dict[str, object]] | None,
    *,
    excluded_non_tests: int,
    excluded_tests: int,
) -> dict[str, dict[str, object]] | None:
    if not scope_payload:
        return None
    non_tests = adjusted_call_sites_payload(
        scope_payload.get("non_tests"),
        excluded_external_likely=excluded_non_tests,
    )
    tests = adjusted_call_sites_payload(
        scope_payload.get("tests"),
        excluded_external_likely=excluded_tests,
    )
    return {"non_tests": non_tests, "tests": tests}


def classification_quality_payload(
    call_sites: dict[str, object] | None,
    *,
    drop_reasons: dict[str, int],
    drop_classification: dict[str, int],
) -> dict[str, object]:
    """Summarize residual classification quality on persisted dropped callsites."""

    dropped = int((call_sites or {}).get("dropped") or 0)
    external_likely = int(drop_classification.get("external_likely", 0))
    ambiguous = int(
        drop_reasons.get("ambiguous_no_in_scope_candidate", 0)
        + drop_reasons.get("ambiguous_multiple_in_scope_candidates", 0)
    )
    external_share = (external_likely / dropped) if dropped > 0 else None
    ambiguous_share = (ambiguous / dropped) if dropped > 0 else None
    confidence = "n/a"
    caveats: list[str] = []
    if dropped > 0:
        confidence = "high"
        if external_share is not None and external_share >= 0.75:
            confidence = "low"
            caveats.append("external_likely_dominates_drops")
        elif external_share is not None and external_share >= 0.40:
            confidence = "medium"
            caveats.append("external_likely_material_share")
        if ambiguous_share is not None and ambiguous_share >= 0.75:
            confidence = "low"
            caveats.append("ambiguity_dominates_drops")
        elif ambiguous_share is not None and ambiguous_share >= 0.40:
            if confidence == "high":
                confidence = "medium"
            caveats.append("ambiguity_material_share")
    return {
        "dropped_callsites": dropped,
        "external_likely": external_likely,
        "ambiguous_drops": ambiguous,
        "external_likely_share": external_share,
        "ambiguous_share": ambiguous_share,
        "confidence": confidence,
        "caveats": caveats,
    }


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
