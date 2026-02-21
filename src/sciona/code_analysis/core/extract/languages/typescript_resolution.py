# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript constructor/instance resolution utilities."""

from __future__ import annotations


def resolve_ts_constructor_name(
    callee_text: str,
    class_name_map: dict[str, str],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> str | None:
    terminal = callee_text.split(".")[-1] if callee_text else ""
    if terminal in class_name_map:
        return class_name_map[terminal]
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
    instance_map: dict[str, str],
    class_instance_map: dict[str, dict[str, str]],
    class_name_map: dict[str, str],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> None:
    for name, callee_text in pending_instance_assignments:
        target = resolve_ts_constructor_name(
            callee_text, class_name_map, import_aliases, member_aliases
        )
        if target:
            instance_map[name] = target
    for class_name, field, callee_text in pending_class_instances:
        target = resolve_ts_constructor_name(
            callee_text, class_name_map, import_aliases, member_aliases
        )
        if target:
            class_instance_map.setdefault(class_name, {})[field] = target
