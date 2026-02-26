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


def aggregate_breakdown(records: Iterable[dict]) -> dict:
    totals: dict[str, int] = {}
    for record in records:
        key = f"{record.get('edge_type')}::{record.get('language')}::{record.get('reason')}"
        totals[key] = totals.get(key, 0) + 1
    return totals
