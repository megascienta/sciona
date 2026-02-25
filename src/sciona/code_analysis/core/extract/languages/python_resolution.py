# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python constructor and instance resolution utilities."""

from __future__ import annotations

from ...normalize.model import FileSnapshot
from .symbol_ir import resolve_alias
from .type_names import type_base_name


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    text = getattr(node, "text", None)
    if text:
        return text.decode("utf-8")
    return content[node.start_byte : node.end_byte].decode("utf-8")


def resolve_constructor_target(
    callee_text: str,
    terminal: str,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> str | None:
    class_match = unique_class_match(terminal, class_name_candidates)
    if class_match:
        return class_match
    if terminal in member_aliases:
        return member_aliases[terminal]
    if "." in callee_text:
        head, rest = callee_text.split(".", 1)
        if head in import_aliases:
            return f"{import_aliases[head]}.{rest}"
        for raw, normalized in raw_module_map.items():
            if callee_text == raw or callee_text.startswith(f"{raw}."):
                suffix = callee_text[len(raw) :].lstrip(".")
                return f"{normalized}.{suffix}" if suffix else normalized
    return None


def collect_module_instance_map(
    root,
    snapshot: FileSnapshot,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    instance_map: dict[str, str] = {}

    def walk(node) -> None:
        if node is None:
            return
        if node.type in {
            "function_definition",
            "async_function_definition",
            "class_definition",
            "lambda",
        }:
            return
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if (
                left is not None
                and right is not None
                and right.type == "call"
                and left.type == "identifier"
            ):
                name = node_text(left, snapshot.content)
                callee = right.child_by_field_name("function")
                callee_text = node_text(callee, snapshot.content) or ""
                terminal = callee_text.split(".")[-1] if callee_text else ""
                target = resolve_constructor_target(
                    callee_text,
                    terminal,
                    class_name_candidates,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
                )
                if name and target:
                    instance_map[name] = target
            elif left is not None and right is not None and left.type == "identifier":
                target = _resolve_alias_target(
                    right,
                    snapshot.content,
                    instance_map,
                )
                name = node_text(left, snapshot.content)
                if name and target:
                    instance_map[name] = target
        for child in getattr(node, "named_children", []):
            walk(child)

    walk(root)
    return instance_map


def collect_callable_instance_map(
    body_node,
    snapshot: FileSnapshot,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    if body_node is None:
        return {}
    instance_map: dict[str, str] = _typed_parameters_for_body_node(
        body_node,
        snapshot,
        class_name_candidates,
        import_aliases,
        member_aliases,
        raw_module_map,
    )

    def walk(node) -> None:
        if node is None:
            return
        if node.type in {"function_definition", "class_definition", "lambda"}:
            return
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if (
                left is not None
                and right is not None
                and right.type == "call"
            ):
                name = None
                if left.type == "identifier":
                    name = node_text(left, snapshot.content)
                elif left.type == "attribute":
                    object_node = left.child_by_field_name("object")
                    attribute_node = left.child_by_field_name("attribute")
                    object_name = node_text(object_node, snapshot.content) or ""
                    if object_name in {"self", "cls"}:
                        name = node_text(attribute_node, snapshot.content)
                    if not name:
                        left_text = node_text(left, snapshot.content) or ""
                        if left_text.startswith("self.") or left_text.startswith("cls."):
                            parts = left_text.split(".", 2)
                            if len(parts) >= 2:
                                name = parts[1]
                callee = right.child_by_field_name("function")
                callee_text = node_text(callee, snapshot.content) or ""
                terminal = callee_text.split(".")[-1] if callee_text else ""
                target = resolve_constructor_target(
                    callee_text,
                    terminal,
                    class_name_candidates,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
                )
                if name and target:
                    instance_map[name] = target
            elif left is not None and right is not None:
                name = None
                if left.type == "identifier":
                    name = node_text(left, snapshot.content)
                elif left.type == "attribute":
                    object_node = left.child_by_field_name("object")
                    attribute_node = left.child_by_field_name("attribute")
                    object_name = node_text(object_node, snapshot.content) or ""
                    if object_name in {"self", "cls"}:
                        name = node_text(attribute_node, snapshot.content)
                if name:
                    target = _resolve_alias_target(
                        right,
                        snapshot.content,
                        instance_map,
                    )
                    if target:
                        instance_map[name] = target
        for child in getattr(node, "named_children", []):
            walk(child)

    walk(body_node)
    return instance_map


def collect_class_instance_map(
    class_body_node,
    snapshot: FileSnapshot,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    if class_body_node is None:
        return {}
    instance_map: dict[str, str] = {}

    def walk(node) -> None:
        if node is None:
            return
        if node.type == "function_definition":
            if any(child.type == "async" for child in getattr(node, "children", [])):
                return
        if node.type in {
            "class_definition",
            "async_function_definition",
            "lambda",
        }:
            return
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left is not None and right is not None and right.type == "call":
                name = None
                if left.type == "attribute":
                    object_node = left.child_by_field_name("object")
                    attribute_node = left.child_by_field_name("attribute")
                    object_name = node_text(object_node, snapshot.content) or ""
                    if object_name in {"self", "cls"}:
                        name = node_text(attribute_node, snapshot.content)
                    if not name:
                        left_text = node_text(left, snapshot.content) or ""
                        if left_text.startswith("self.") or left_text.startswith("cls."):
                            parts = left_text.split(".", 2)
                            if len(parts) >= 2:
                                name = parts[1]
                if name:
                    callee = right.child_by_field_name("function")
                    callee_text = node_text(callee, snapshot.content) or ""
                    terminal = callee_text.split(".")[-1] if callee_text else ""
                    target = resolve_constructor_target(
                        callee_text,
                        terminal,
                        class_name_candidates,
                        import_aliases,
                        member_aliases,
                        raw_module_map,
                    )
                    if target:
                        instance_map[name] = target
            elif left is not None and right is not None and left.type == "attribute":
                object_node = left.child_by_field_name("object")
                attribute_node = left.child_by_field_name("attribute")
                object_name = node_text(object_node, snapshot.content) or ""
                if object_name in {"self", "cls"}:
                    name = node_text(attribute_node, snapshot.content)
                    alias_scope = dict(instance_map)
                    alias_scope.update(
                        _typed_parameters_for_enclosing_callable(
                            left,
                            snapshot,
                            class_name_candidates,
                            import_aliases,
                            member_aliases,
                            raw_module_map,
                        )
                    )
                    target = _resolve_alias_target(right, snapshot.content, alias_scope)
                    if name and target:
                        instance_map[name] = target
        for child in getattr(node, "named_children", []):
            walk(child)

    walk(class_body_node)
    return instance_map


def _resolve_alias_target(
    node,
    content: bytes,
    known_instances: dict[str, str],
) -> str | None:
    if node is None:
        return None
    if node.type == "identifier":
        name = node_text(node, content)
        return resolve_alias(name or "", instance_map=known_instances)
    if node.type == "attribute":
        base = node_text(node, content) or ""
        if base.startswith("self.") or base.startswith("cls."):
            parts = base.split(".", 2)
            if len(parts) >= 2:
                return resolve_alias(parts[1], instance_map=known_instances)
        return resolve_alias(base, instance_map=known_instances)
    return None


def unique_class_match(
    simple_name: str,
    class_name_candidates: dict[str, set[str]],
) -> str | None:
    candidates = class_name_candidates.get(simple_name) or set()
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def _typed_parameters_for_enclosing_callable(
    node,
    snapshot: FileSnapshot,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    current = getattr(node, "parent", None)
    while current is not None:
        if current.type in {"function_definition", "async_function_definition"}:
            return _typed_parameters_for_callable_node(
                current,
                snapshot,
                class_name_candidates,
                import_aliases,
                member_aliases,
                raw_module_map,
            )
        current = getattr(current, "parent", None)
    return {}


def _typed_parameters_for_body_node(
    body_node,
    snapshot: FileSnapshot,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    callable_node = getattr(body_node, "parent", None)
    if callable_node is None or callable_node.type not in {
        "function_definition",
        "async_function_definition",
    }:
        return {}
    return _typed_parameters_for_callable_node(
        callable_node,
        snapshot,
        class_name_candidates,
        import_aliases,
        member_aliases,
        raw_module_map,
    )


def _typed_parameters_for_callable_node(
    callable_node,
    snapshot: FileSnapshot,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    params_node = callable_node.child_by_field_name("parameters")
    if params_node is None:
        return {}
    typed: dict[str, str] = {}
    for child in getattr(params_node, "named_children", []):
        if child.type != "typed_parameter":
            continue
        name_node = child.child_by_field_name("name")
        if name_node is None:
            name_node = next(
                (
                    n
                    for n in getattr(child, "named_children", [])
                    if n.type == "identifier"
                ),
                None,
            )
        type_node = child.child_by_field_name("type")
        name = node_text(name_node, snapshot.content) if name_node else None
        type_text = node_text(type_node, snapshot.content) if type_node else None
        normalized_type = type_base_name(type_text) if type_text else None
        if not name or name in {"self", "cls"} or not normalized_type:
            continue
        terminal = normalized_type.split(".")[-1] if normalized_type else ""
        target = resolve_constructor_target(
            normalized_type or type_text,
            terminal,
            class_name_candidates,
            import_aliases,
            member_aliases,
            raw_module_map,
        )
        if target:
            typed[name] = target
    return typed
