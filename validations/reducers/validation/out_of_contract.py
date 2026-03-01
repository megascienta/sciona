# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Iterable


IN_REPO_UNRESOLVED_REASON_MAP: dict[str, str] = {
    "no_candidates": "in_repo_unresolved_no_candidates",
    "unique_without_provenance": "in_repo_unresolved_unique_without_provenance",
    "ambiguous_no_caller_module": "in_repo_unresolved_ambiguous_no_caller_module",
    "ambiguous_no_in_scope_candidate": "in_repo_unresolved_ambiguous_no_in_scope_candidate",
    "ambiguous_multiple_in_scope_candidates": "in_repo_unresolved_ambiguous_multiple_in_scope_candidates",
}


def is_in_repo_unresolved_reason(reason: str) -> bool:
    value = (reason or "").strip()
    return value == "in_repo_unresolved" or value.startswith("in_repo_unresolved_")


def classify_call_reason(
    *,
    edge,
    language: str,
    call_resolution: dict,
    dropped_reason: str | None = None,
) -> str:
    del language
    callee_text = (getattr(edge, "callee_text", None) or "").strip().lower()
    if edge.dynamic:
        if callee_text.startswith("decorator:"):
            return "decorator"
        return "dynamic"
    identifier = (edge.callee or "").strip()
    if not identifier and edge.callee_qname:
        identifier = edge.callee_qname.split(".")[-1]
    if not identifier:
        return "unknown"
    symbol_index: dict[str, list[str]] = call_resolution.get("symbol_index", {})
    if identifier in symbol_index:
        normalized_drop = (dropped_reason or "").strip()
        if normalized_drop:
            return IN_REPO_UNRESOLVED_REASON_MAP.get(normalized_drop, "in_repo_unresolved")
        return "in_repo_unresolved"
    return "external"


def classify_call_semantic_type(*, edge, reason: str) -> str:
    callee_text = (getattr(edge, "callee_text", None) or "").strip()
    has_member_shape = "." in callee_text if callee_text else False
    if reason == "decorator":
        return "decorator_call"
    if reason == "dynamic":
        return "dynamic_member_call" if has_member_shape else "dynamic_call"
    if is_in_repo_unresolved_reason(reason):
        return "member_call_unresolved" if has_member_shape else "direct_call_unresolved"
    if reason == "unknown":
        return "unknown_call_shape"
    if reason == "external":
        return "external_call"
    return "other_call_unresolved"


def classify_import_reason(
    *,
    raw_target: str,
    resolved: str | None,
    repo_prefix: str,
) -> str:
    if not raw_target:
        return "unknown"
    if resolved:
        return "in_repo_unresolved"
    if raw_target.startswith(".") or raw_target.startswith("/"):
        return "relative_unresolved"
    if repo_prefix and (
        raw_target == repo_prefix or raw_target.startswith(f"{repo_prefix}.")
    ):
        return "in_repo_unresolved"
    return "external"


def classify_import_semantic_type(*, raw_target: str, reason: str) -> str:
    target = (raw_target or "").strip()
    if reason == "relative_unresolved":
        return "relative_import_unresolved"
    if reason == "in_repo_unresolved":
        if target.startswith("@"):
            return "aliased_import_unresolved"
        return "module_import_unresolved"
    if reason == "external":
        return "external_import"
    if reason == "unknown":
        return "unknown_import_shape"
    return "other_import_unresolved"


def aggregate_breakdown(records: Iterable[dict]) -> dict:
    totals: dict[str, int] = {}
    for record in records:
        key = f"{record.get('edge_type')}::{record.get('language')}::{record.get('reason')}"
        totals[key] = totals.get(key, 0) + 1
    return totals
