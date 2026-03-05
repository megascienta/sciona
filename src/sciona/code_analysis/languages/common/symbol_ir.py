# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared typed-symbol IR utilities used by language resolvers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TypedSymbolBinding:
    symbol: str
    target_type: str
    source: str


def resolve_alias(
    symbol: str,
    *,
    instance_map: dict[str, str],
    class_name_map: dict[str, str] | None = None,
    import_aliases: dict[str, str] | None = None,
    member_aliases: dict[str, str] | None = None,
) -> str | None:
    if symbol in instance_map:
        return instance_map[symbol]
    if class_name_map and symbol in class_name_map:
        return class_name_map[symbol]
    if import_aliases and symbol in import_aliases:
        return import_aliases[symbol]
    if member_aliases and symbol in member_aliases:
        return member_aliases[symbol]
    return None


def binding_map(bindings: list[TypedSymbolBinding]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for binding in bindings:
        if binding.symbol and binding.target_type:
            mapped[binding.symbol] = binding.target_type
    return mapped

