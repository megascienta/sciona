# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer list rendering helpers."""

from __future__ import annotations

import inspect
from typing import Iterable, Mapping


CATEGORY_ORDER = [
    "discovery",
    "navigation",
    "structure",
    "relations",
    "metrics",
    "source",
]


def format_reducer_call(reducer_id: str, reducer_module) -> str:
    signature = getattr(reducer_module, "render", None)
    if signature is None:
        return f"reducer --id {reducer_id}"
    sig = inspect.signature(signature)
    options: list[str] = []
    for name, param in sig.parameters.items():
        if name in {"snapshot_id", "conn", "repo_root"}:
            continue
        if param.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue
        flag = f"--{name.replace('_', '-')}"
        if name == "extras":
            options.append(f"[{flag}]")
            continue
        metavar = name.upper()
        if param.default is inspect._empty:
            options.append(f"{flag} {metavar}")
        else:
            options.append(f"[{flag} {metavar}]")
    rendered = " ".join(options)
    if rendered:
        return f"reducer --id {reducer_id} {rendered}"
    return f"reducer --id {reducer_id}"


def render_reducer_list(
    entries: Iterable[Mapping[str, object]],
    reducers,
    *,
    include_prefix: bool = True,
) -> list[str]:
    bucket: dict[str, list[Mapping[str, object]]] = {}
    for entry in entries:
        category = str(entry.get("category") or "unknown")
        bucket.setdefault(category, []).append(entry)

    for values in bucket.values():
        values.sort(key=lambda item: str(item.get("reducer_id") or ""))

    ordered_categories: list[str] = []
    for category in CATEGORY_ORDER:
        if category in bucket:
            ordered_categories.append(category)
    for category in sorted(set(bucket.keys()) - set(CATEGORY_ORDER)):
        ordered_categories.append(category)

    prefix = "sciona " if include_prefix else ""
    lines = []
    for category in ordered_categories:
        lines.append(f"Category: {category}")
        lines.append("")
        for entry in bucket.get(category, []):
            reducer_id = str(entry.get("reducer_id") or "").strip()
            reducer_entry = reducers.get(reducer_id)
            reducer_module = getattr(reducer_entry, "module", reducer_entry)
            if reducer_module is None:
                continue
            summary = str(entry.get("summary") or "").strip()
            lines.append(f"  Summary: {summary}")
            call = format_reducer_call(reducer_id, reducer_module)
            lines.append(f"  Command: {prefix}{call}")
            lines.append("")
    return lines


def render_reducer_catalog(entries: Iterable[Mapping[str, object]]) -> list[str]:
    bucket: dict[str, list[Mapping[str, object]]] = {}
    for entry in entries:
        category = str(entry.get("category") or "unknown")
        bucket.setdefault(category, []).append(entry)

    for values in bucket.values():
        values.sort(key=lambda item: str(item.get("reducer_id") or ""))

    ordered_categories: list[str] = []
    for category in CATEGORY_ORDER:
        if category in bucket:
            ordered_categories.append(category)
    for category in sorted(set(bucket.keys()) - set(CATEGORY_ORDER)):
        ordered_categories.append(category)

    lines = ["Available reducers:"]
    for category in ordered_categories:
        lines.append(f"Category: {category}")
        for entry in bucket.get(category, []):
            reducer_id = str(entry.get("reducer_id") or "").strip()
            summary = str(entry.get("summary") or "").strip()
            lines.append(f"- {reducer_id}")
            lines.append(f"  Summary: {summary}")
    return lines


__all__ = [
    "CATEGORY_ORDER",
    "format_reducer_call",
    "render_reducer_list",
    "render_reducer_catalog",
]
