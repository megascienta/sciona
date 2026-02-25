# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript constructor/instance resolution utilities."""

from __future__ import annotations

from .symbol_ir import resolve_alias


def resolve_ts_constructor_name(
    callee_text: str,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> str | None:
    terminal = callee_text.split(".")[-1] if callee_text else ""
    candidates = class_name_candidates.get(terminal) or set()
    if len(candidates) == 1:
        return next(iter(candidates))
    if terminal in member_aliases:
        return member_aliases[terminal]
    if "." in callee_text:
        head, rest = callee_text.split(".", 1)
        if head in import_aliases:
            return f"{import_aliases[head]}.{rest}"
    return None


def resolve_pending_instances(
    pending_instance_assignments: list[tuple[str, str]],
    pending_class_instances: list[tuple[str, str, str]],
    pending_alias_assignments: list[tuple[str, str]],
    pending_class_aliases: list[tuple[str, str, str]],
    instance_map: dict[str, str],
    class_instance_map: dict[str, dict[str, str]],
    class_name_candidates: dict[str, set[str]],
    class_name_map: dict[str, str],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> None:
    for name, callee_text in pending_instance_assignments:
        target = resolve_ts_constructor_name(
            callee_text, class_name_candidates, import_aliases, member_aliases
        )
        if target:
            instance_map[name] = target
    for class_name, field, callee_text in pending_class_instances:
        target = resolve_ts_constructor_name(
            callee_text, class_name_candidates, import_aliases, member_aliases
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
