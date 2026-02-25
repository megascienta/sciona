# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Normalization helpers for extracted call identifiers."""

from __future__ import annotations

from typing import Sequence


def normalize_call_identifiers(
    resolved_calls: Sequence[tuple[str, str, str, Sequence[str]]],
) -> list[tuple[str, str, str, list[str]]]:
    terminal_map_by_scope: dict[tuple[str, str], dict[str, str | None]] = {}
    for language, qualified, node_type, identifiers in resolved_calls:
        scope = _module_scope_for_call(qualified, node_type)
        bucket = terminal_map_by_scope.setdefault((language, scope), {})
        for identifier in identifiers:
            if "." not in identifier:
                continue
            terminal = identifier.rsplit(".", 1)[-1]
            existing = bucket.get(terminal)
            if existing is None and terminal in bucket:
                continue
            if existing is None:
                bucket[terminal] = identifier
            elif existing != identifier:
                bucket[terminal] = None
    normalized: list[tuple[str, str, str, list[str]]] = []
    for language, qualified, node_type, identifiers in resolved_calls:
        scope = _module_scope_for_call(qualified, node_type)
        terminal_map = terminal_map_by_scope.get((language, scope), {})
        updated: list[str] = []
        for identifier in identifiers:
            if "." in identifier:
                updated.append(identifier)
            else:
                mapped = terminal_map.get(identifier)
                if mapped:
                    updated.append(mapped)
                else:
                    updated.append(identifier)
        normalized.append((language, qualified, node_type, updated))
    return normalized


def _module_scope_for_call(qualified_name: str, node_type: str) -> str:
    parts = qualified_name.split(".")
    if node_type == "method":
        if len(parts) > 2:
            return ".".join(parts[:-2])
        return qualified_name
    if len(parts) > 1:
        return ".".join(parts[:-1])
    return qualified_name


__all__ = ["_module_scope_for_call", "normalize_call_identifiers"]
