# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Iterable


def classify_call_reason(
    *,
    edge,
    language: str,
    call_resolution: dict,
) -> str:
    del language
    callee_text = (getattr(edge, "callee_text", None) or "").strip().lower()
    if callee_text.startswith("decorator:") or callee_text == "decorator":
        return "decorator"
    if edge.dynamic:
        return "dynamic"
    identifier = (edge.callee or "").strip()
    if not identifier and edge.callee_qname:
        identifier = edge.callee_qname.split(".")[-1]
    if not identifier:
        return "unknown"
    symbol_index: dict[str, list[str]] = call_resolution.get("symbol_index", {})
    if identifier in symbol_index:
        return "in_repo_unresolved"
    return "external"


def classify_call_semantic_type(*, edge, reason: str) -> str:
    callee_text = (getattr(edge, "callee_text", None) or "").strip()
    has_member_shape = "." in callee_text if callee_text else False
    if reason == "dynamic":
        return "dynamic_member_call" if has_member_shape else "dynamic_call"
    if reason == "decorator":
        return "decorator_call"
    if reason == "in_repo_unresolved":
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
