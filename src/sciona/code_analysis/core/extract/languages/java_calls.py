# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java call extraction and resolution utilities."""

from __future__ import annotations

from typing import List

from ....tools.call_extraction import CallTarget


def callee_text(call_node, callee_node, content: bytes) -> str | None:
    if call_node is None:
        return node_text(callee_node, content)
    if call_node.type == "method_invocation":
        name_node = call_node.child_by_field_name("name")
        object_node = call_node.child_by_field_name("object")
        name = node_text(name_node or callee_node, content)
        if object_node is not None:
            obj = node_text(object_node, content)
            if obj and name:
                return f"{obj}.{name}"
        return name
    if call_node.type == "object_creation_expression":
        type_node = call_node.child_by_field_name("type")
        return node_text(type_node, content) or node_text(callee_node, content)
    return node_text(callee_node, content)


def resolve_java_calls(
    targets: List[CallTarget],
    module_name: str,
    module_functions: set[str],
    class_methods: dict[str, set[str]],
    class_name_map: dict[str, str],
    import_class_map: dict[str, str],
    class_name: str | None,
    instance_types: dict[str, str],
    module_prefix: str | None,
    qualify_java_type,
) -> List[str]:
    resolved: list[str] = []
    class_method_names = class_methods.get(class_name, set()) if class_name else set()
    for target in targets:
        terminal = target.terminal
        raw = (target.callee_text or "").strip()
        if "." in raw:
            receiver = raw.rsplit(".", 1)[0].strip()
            receiver_simple = receiver.rsplit(".", 1)[-1]
            instance_type = instance_types.get(receiver_simple)
            if instance_type:
                qualified_type = qualify_java_type(
                    instance_type,
                    module_name,
                    class_name_map,
                    import_class_map,
                    module_prefix,
                )
                if qualified_type:
                    resolved.append(f"{qualified_type}.{terminal}")
                    continue
            import_target = import_class_map.get(receiver_simple)
            local_class = class_name_map.get(receiver_simple)
            if import_target:
                resolved.append(f"{import_target}.{terminal}")
                continue
            if local_class:
                resolved.append(f"{local_class}.{terminal}")
                continue
        if is_unqualified(raw):
            import_target = import_class_map.get(terminal)
            local_class = class_name_map.get(terminal)
            if import_target:
                resolved.append(f"{import_target}.{terminal}")
                continue
            if local_class:
                resolved.append(f"{local_class}.{terminal}")
                continue
        if class_name and terminal in class_method_names:
            if is_receiver_call(raw) or is_unqualified(raw):
                resolved.append(f"{class_name}.{terminal}")
                continue
        if is_unqualified(raw) and terminal in module_functions:
            resolved.append(f"{module_name}.{terminal}")
            continue
        class_qualified = class_name_map.get(terminal)
        if class_qualified and terminal in class_methods.get(class_qualified, set()):
            resolved.append(f"{class_qualified}.{terminal}")
            continue
        resolved.append(terminal)
    return resolved


def is_unqualified(callee_text_raw: str) -> bool:
    return "." not in callee_text_raw


def is_receiver_call(callee_text_raw: str) -> bool:
    return callee_text_raw.startswith("this.") or callee_text_raw.startswith("super.")


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    return content[node.start_byte : node.end_byte].decode("utf-8")
