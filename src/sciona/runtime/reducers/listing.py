# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer list rendering helpers."""

from __future__ import annotations

import inspect
from typing import Mapping, Union, get_args, get_origin

from .metadata import CATEGORY_ORDER


def normalize_category(category: object) -> str:
    value = str(category).strip()
    if value:
        return value
    return "unknown"


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
        if _is_bool_parameter(param):
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


def compact_mode_hint(reducer_module) -> str | None:
    signature = getattr(reducer_module, "render", None)
    if signature is None:
        return None
    sig = inspect.signature(signature)
    if "compact" not in sig.parameters:
        return None
    if "top_k" in sig.parameters:
        return "`--compact` [`--top-k` TOP_K]"
    return "`--compact`"


def _is_bool_parameter(param: inspect.Parameter) -> bool:
    annotation = param.annotation
    if annotation is bool:
        return True
    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if args:
        return len(args) == 1 and args[0] is bool
    origin = get_origin(annotation)
    if origin is Union:
        return False
    return False


def render_reducer_list(
    entries: list[Mapping[str, object]],
    reducers,
    *,
    include_prefix: bool = True,
) -> list[str]:
    bucket: dict[str, list[Mapping[str, object]]] = {}
    for entry in entries:
        category = normalize_category(entry.get("category"))
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
            compact_hint = compact_mode_hint(reducer_module)
            if compact_hint:
                lines.append(f"  Compact: yes ({compact_hint})")
            lines.append("")
    return lines


def render_reducer_catalog(entries: list[Mapping[str, object]]) -> list[str]:
    bucket: dict[str, list[Mapping[str, object]]] = {}
    for entry in entries:
        category = normalize_category(entry.get("category"))
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
    "compact_mode_hint",
    "format_reducer_call",
    "normalize_category",
    "render_reducer_catalog",
    "render_reducer_list",
]
