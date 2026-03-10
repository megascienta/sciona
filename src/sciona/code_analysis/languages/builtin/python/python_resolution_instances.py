# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Instance map collection for Python extraction."""

from __future__ import annotations

from ....core.normalize_model import FileSnapshot
from .python_resolution_aliases import (
    _callable_chain,
    _resolve_alias_target,
    attribute_chain,
    node_text,
    resolve_constructor_target,
)
from .python_resolution_types import (
    _typed_parameters_for_body_node,
    _typed_parameters_for_enclosing_callable,
)


def _known_class_targets(
    class_name_candidates: dict[str, set[str]],
) -> set[str]:
    targets: set[str] = set()
    for candidates in class_name_candidates.values():
        targets.update(candidates)
    return targets


def _collect_identifier_names(node, content: bytes) -> set[str]:
    names: set[str] = set()
    if node is None:
        return names
    if node.type == "identifier":
        value = node_text(node, content)
        if value:
            names.add(value)
        return names
    for child in getattr(node, "named_children", []):
        names.update(_collect_identifier_names(child, content))
    return names


def collect_callable_local_bindings(
    body_node,
    snapshot: FileSnapshot,
) -> set[str]:
    """Collect local binding names that can shadow module-level callables."""

    if body_node is None:
        return set()
    names: set[str] = set()
    callable_node = getattr(body_node, "parent", None)
    if callable_node is not None and callable_node.type in {
        "function_definition",
        "async_function_definition",
    }:
        params_node = callable_node.child_by_field_name("parameters")
        for child in getattr(params_node, "named_children", []) if params_node else []:
            name_node = child.child_by_field_name("name")
            if name_node is None and child.type == "identifier":
                name_node = child
            if name_node is not None:
                value = node_text(name_node, snapshot.content)
                if value and value not in {"self", "cls"}:
                    names.add(value)

    def walk(node) -> None:
        if node is None:
            return
        if node.type in {"function_definition", "class_definition", "lambda"}:
            return
        if node.type in {"assignment", "for_statement", "with_item"}:
            left = node.child_by_field_name("left") or node.child_by_field_name("pattern")
            if left is None and node.type == "with_item":
                left = node.child_by_field_name("alias")
            names.update(_collect_identifier_names(left, snapshot.content))
        for child in getattr(node, "named_children", []):
            walk(child)

    walk(body_node)
    names.discard("self")
    names.discard("cls")
    return names


def collect_module_instance_map(
    root,
    snapshot: FileSnapshot,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    instance_map: dict[str, str] = {}
    class_targets = _known_class_targets(class_name_candidates)

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
                callee_chain = _callable_chain(callee, snapshot.content)
                target = resolve_constructor_target(
                    callee_chain,
                    None,
                    class_name_candidates,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
                )
                if name and target and target in class_targets:
                    instance_map[name] = target
            elif left is not None and right is not None and left.type == "identifier":
                target = _resolve_alias_target(
                    right,
                    snapshot.content,
                    instance_map,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
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
    class_targets = _known_class_targets(class_name_candidates)
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
                    chain = attribute_chain(left, snapshot.content)
                    if len(chain) >= 2 and chain[0] in {"self", "cls"}:
                        name = chain[1]
                callee = right.child_by_field_name("function")
                callee_chain = _callable_chain(callee, snapshot.content)
                target = resolve_constructor_target(
                    callee_chain,
                    None,
                    class_name_candidates,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
                )
                if name and target and target in class_targets:
                    instance_map[name] = target
            elif left is not None and right is not None:
                name = None
                if left.type == "identifier":
                    name = node_text(left, snapshot.content)
                elif left.type == "attribute":
                    chain = attribute_chain(left, snapshot.content)
                    if len(chain) >= 2 and chain[0] in {"self", "cls"}:
                        name = chain[1]
                if name:
                    target = _resolve_alias_target(
                        right,
                        snapshot.content,
                        instance_map,
                        import_aliases,
                        member_aliases,
                        raw_module_map,
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
    class_targets = _known_class_targets(class_name_candidates)

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
                    chain = attribute_chain(left, snapshot.content)
                    if len(chain) >= 2 and chain[0] in {"self", "cls"}:
                        name = chain[1]
                if name:
                    callee = right.child_by_field_name("function")
                    callee_chain = _callable_chain(callee, snapshot.content)
                    target = resolve_constructor_target(
                        callee_chain,
                        None,
                        class_name_candidates,
                        import_aliases,
                        member_aliases,
                        raw_module_map,
                    )
                    if target and target in class_targets:
                        instance_map[name] = target
            elif left is not None and right is not None and left.type == "attribute":
                chain = attribute_chain(left, snapshot.content)
                if len(chain) >= 2 and chain[0] in {"self", "cls"}:
                    name = chain[1]
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
                    target = _resolve_alias_target(
                        right,
                        snapshot.content,
                        alias_scope,
                        import_aliases,
                        member_aliases,
                        raw_module_map,
                    )
                    if name and target:
                        instance_map[name] = target
        for child in getattr(node, "named_children", []):
            walk(child)

    walk(class_body_node)
    return instance_map


__all__ = [
    "collect_callable_local_bindings",
    "collect_callable_instance_map",
    "collect_class_instance_map",
    "collect_module_instance_map",
]
