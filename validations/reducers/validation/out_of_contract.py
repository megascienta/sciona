# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Iterable


def standard_call_names(contract: dict, language: str | None = None) -> set[str]:
    out = contract.get("out_of_contract", {}) or {}
    by_language = out.get("standard_calls_by_language") or {}
    if language:
        block = by_language.get(language)
        if block is None:
            block = out.get("standard_calls", []) or []
    else:
        block = out.get("standard_calls", []) or []
        if not block and isinstance(by_language, dict):
            merged: list[str] = []
            for values in by_language.values():
                if isinstance(values, list):
                    merged.extend(values)
            block = merged
    return {name for name in block if isinstance(name, str) and name}


def classify_call_reason(
    *,
    edge,
    language: str,
    call_resolution: dict,
    contract: dict,
) -> str:
    if edge.dynamic:
        return "dynamic"
    standard = standard_call_names(contract, language)
    if edge.callee and edge.callee in standard:
        return "standard_call"
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
    if reason == "in_repo_unresolved":
        return "member_call_unresolved" if has_member_shape else "direct_call_unresolved"
    if reason == "unknown":
        return "unknown_call_shape"
    if reason == "external":
        return "external_call"
    if reason == "standard_call":
        return "standard_call"
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
