# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript constructor/instance resolution utilities."""

from __future__ import annotations

from .symbol_ir import resolve_alias
from .typescript_node_text import node_text, parse_type_annotation, typed_constructor_parameters

_NESTED_FUNCTION_NODE_TYPES = {
    "arrow_function",
    "function",
    "function_expression",
    "function_declaration",
}


def resolve_ts_constructor_name(
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
        target = resolve_ts_constructor_name(
            callee_chain, class_name_candidates, import_aliases, member_aliases
        )
        if target:
            instance_map[name] = target
    for class_name, field, callee_chain in pending_class_instances:
        target = resolve_ts_constructor_name(
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


def collect_callable_typed_binding_instance_map(
    body_node,
    *,
    content: bytes,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> dict[str, str]:
    """Resolve callable-scoped typed bindings (params + local declarators)."""

    if body_node is None:
        return {}

    resolved: dict[str, str] = {}
    callable_node = getattr(body_node, "parent", None)
    for param_name, type_chain in typed_constructor_parameters(callable_node, content):
        target = resolve_ts_constructor_name(
            type_chain,
            class_name_candidates,
            import_aliases,
            member_aliases,
        )
        if target:
            resolved[param_name] = target

    stack: list[object] = [body_node]
    while stack:
        node = stack.pop()
        node_type = getattr(node, "type", None)
        if node_type in _NESTED_FUNCTION_NODE_TYPES:
            continue
        if node_type in {"class", "class_expression", "class_declaration"}:
            continue
        if node_type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            type_node = node.child_by_field_name("type")
            if (
                name_node is not None
                and getattr(name_node, "type", None) == "identifier"
                and type_node is not None
            ):
                var_name = node_text(name_node, content)
                type_chain = parse_type_annotation(type_node, content)
                target = resolve_ts_constructor_name(
                    type_chain,
                    class_name_candidates,
                    import_aliases,
                    member_aliases,
                )
                if var_name and target:
                    resolved[var_name] = target
        named_children = getattr(node, "named_children", None)
        if named_children is None:
            named_children = getattr(node, "children", [])
        stack.extend(reversed(list(named_children)))

    return resolved
