# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript call resolution utilities."""

from __future__ import annotations

from typing import List

from ....tools.call_extraction import CallTarget


def resolve_typescript_calls(
    targets: List[CallTarget],
    module_name: str,
    module_functions: set[str],
    class_methods: dict[str, set[str]],
    class_name: str | None,
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    class_name_map: dict[str, str],
    instance_map: dict[str, str],
    class_instance_map: dict[str, dict[str, str]],
) -> List[str]:
    resolved: list[str] = []
    class_method_names = class_methods.get(class_name, set()) if class_name else set()
    for target in targets:
        terminal = target.terminal
        callee_text = (target.callee_text or "").strip()
        if "." in callee_text:
            head, rest = callee_text.split(".", 1)
            if head in instance_map:
                resolved.append(f"{instance_map[head]}.{terminal}")
                continue
            if head in class_name_map:
                resolved.append(f"{class_name_map[head]}.{terminal}")
                continue
            if class_name and callee_text.startswith("this."):
                parts = callee_text.split(".")
                if len(parts) >= 3:
                    field = parts[1]
                    target_class = class_instance_map.get(class_name, {}).get(field)
                    if target_class:
                        resolved.append(f"{target_class}.{terminal}")
                        continue
            if head in import_aliases:
                resolved.append(f"{import_aliases[head]}.{rest}")
                continue
        if terminal in member_aliases:
            resolved.append(member_aliases[terminal])
            continue
        if class_name and is_receiver_call(callee_text) and terminal in class_method_names:
            resolved.append(f"{class_name}.{terminal}")
            continue
        if is_unqualified(callee_text) and terminal in module_functions:
            resolved.append(f"{module_name}.{terminal}")
            continue
        resolved.append(terminal)
    return resolved


def is_unqualified(callee_text: str) -> bool:
    return "." not in callee_text


def is_receiver_call(callee_text: str) -> bool:
    return callee_text.startswith("this.") or callee_text.startswith("super.")
