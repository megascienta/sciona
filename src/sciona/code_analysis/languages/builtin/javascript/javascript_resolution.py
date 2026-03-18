# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""JavaScript constructor/instance resolution utilities."""

from __future__ import annotations

from ...common.ir.symbol_ir import resolve_alias


def resolve_js_constructor_name(
    callee_chain: tuple[str, ...],
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> str | None:
    if not callee_chain:
        return None
    terminal = callee_chain[-1]
    candidates = class_name_candidates.get(terminal) or set()
    if len(candidates) == 1:
        return next(iter(candidates))
    if terminal in member_aliases:
        return member_aliases[terminal]
    if len(callee_chain) > 1:
        head = callee_chain[0]
        if head in import_aliases:
            return f"{import_aliases[head]}.{'.'.join(callee_chain[1:])}"
    return None


def resolve_pending_instances(
    pending_instance_assignments: list[tuple[str, tuple[str, ...]]],
    pending_class_instances: list[tuple[str, str, tuple[str, ...]]],
    pending_alias_assignments: list[tuple[str, str]],
    pending_class_aliases: list[tuple[str, str, str]],
    instance_map: dict[str, str],
    class_instance_map: dict[str, dict[str, str]],
    class_name_candidates: dict[str, set[str]],
    class_name_map: dict[str, str],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> None:
    for name, callee_chain in pending_instance_assignments:
        target = resolve_js_constructor_name(
            callee_chain, class_name_candidates, import_aliases, member_aliases
        )
        if target:
            instance_map[name] = target
    for class_name, field, callee_chain in pending_class_instances:
        target = resolve_js_constructor_name(
            callee_chain, class_name_candidates, import_aliases, member_aliases
        )
        if target:
            class_instance_map.setdefault(class_name, {})[field] = target
    for name, source in pending_alias_assignments:
        target = resolve_alias(
            source,
            instance_map=instance_map,
            class_name_map=class_name_map,
            import_aliases=import_aliases,
            member_aliases=member_aliases,
        )
        if target:
            instance_map[name] = target
    for class_name, field, source_field in pending_class_aliases:
        source_target = class_instance_map.get(class_name, {}).get(source_field)
        if source_target:
            class_instance_map.setdefault(class_name, {})[field] = source_target


__all__ = ["resolve_pending_instances"]
