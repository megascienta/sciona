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


def format_reducer_call(reducer_id: str, reducer_module, args_meta=None) -> str:
    signature = getattr(reducer_module, "render", None)
    if signature is None:
        return f"reducer --id {reducer_id}"
    required_names = {
        str(arg.get("name")) for arg in (args_meta or []) if arg.get("required")
    }
    sig = _render_signature(signature)
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
        metavar = name.upper()
        if name in required_names:
            options.append(f"{flag} {metavar}")
            continue
        if name == "extras":
            options.append(f"[{flag}]")
            continue
        if _is_bool_parameter(param):
            options.append(f"[{flag}]")
            continue
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
    sig = _render_signature(signature)
    if "compact" not in sig.parameters:
        return None
    parts = ["`--compact`"]
    for name in ("top_k", "limit", "depth"):
        if name in sig.parameters:
            parts.append(f"[`--{name.replace('_', '-')}` {name.upper()}]")
    return " ".join(parts)


def _render_signature(render) -> inspect.Signature:
    try:
        return inspect.signature(render, eval_str=True)
    except Exception:
        return inspect.signature(render)


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
            call = format_reducer_call(reducer_id, reducer_module, entry.get("args"))
            lines.append(f"  Command: {prefix}{call}")
            compact_hint = compact_mode_hint(reducer_module)
            if compact_hint:
                lines.append(f"  Compact: yes ({compact_hint})")
            lines.append("")
    return lines


def render_reducer_usage_notes(
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
    lines = ["Reducer argument vocabulary:"]
    for category in ordered_categories:
        lines.append(f"- {category}:")
        for entry in bucket.get(category, []):
            reducer_id = str(entry.get("reducer_id") or "").strip()
            reducer_entry = reducers.get(reducer_id)
            reducer_module = getattr(reducer_entry, "module", reducer_entry)
            if reducer_module is None:
                continue
            call = format_reducer_call(reducer_id, reducer_module, entry.get("args"))
            lines.append(f"  - `{reducer_id}`: `{prefix}{call}`")
            requires = str(entry.get("requires") or "").strip()
            if requires:
                lines.append(f"    Requires: {requires}")
            args = entry.get("args") or []
            if not args:
                lines.append("    Arguments: none")
                continue
            lines.append("    Arguments:")
            for arg in args:
                rendered = _format_argument_usage(arg)
                if rendered:
                    lines.append(f"    - {rendered}")
    return lines


def _format_argument_usage(arg: object) -> str:
    if not isinstance(arg, Mapping):
        return ""
    name = str(arg.get("name") or "").strip()
    if not name:
        return ""
    arg_type = str(arg.get("type") or "value").strip()
    flag = f"--{name.replace('_', '-')}"
    if arg_type == "bool":
        rendered_flag = f"`{flag}`"
    else:
        rendered_flag = f"`{flag} {name.upper()}`"
    qualifiers = [arg_type]
    qualifiers.append("required" if bool(arg.get("required")) else "optional")
    enum = [str(value) for value in (arg.get("enum") or []) if str(value)]
    if enum:
        qualifiers.append("one of: " + ", ".join(enum))
    default = arg.get("default")
    if default is not None:
        qualifiers.append(f"default: {default}")
    description = str(arg.get("description") or "").strip()
    suffix = f" - {description}" if description else ""
    return f"{rendered_flag}: {'; '.join(qualifiers)}{suffix}"


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
    "render_reducer_usage_notes",
]
