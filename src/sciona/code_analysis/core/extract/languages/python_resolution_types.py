# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Typed-parameter resolution helpers for Python extraction."""

from __future__ import annotations

from ...normalize.model import FileSnapshot
from .python_resolution_aliases import _callable_chain, node_text, resolve_constructor_target
from .type_names import type_base_name


def _type_annotation_chain(node, content: bytes) -> tuple[str, ...]:
    if node is None:
        return ()
    if node.type in {"identifier", "attribute"}:
        return _callable_chain(node, content)
    for child in getattr(node, "named_children", []):
        nested = _type_annotation_chain(child, content)
        if nested:
            return nested
    return ()


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
        type_chain = _type_annotation_chain(type_node, snapshot.content)
        terminal = normalized_type.split(".")[-1] if normalized_type else ""
        target = resolve_constructor_target(
            type_chain,
            terminal,
            class_name_candidates,
            import_aliases,
            member_aliases,
            raw_module_map,
        )
        if target:
            typed[name] = target
    return typed


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


__all__ = [
    "_type_annotation_chain",
    "_typed_parameters_for_body_node",
    "_typed_parameters_for_callable_node",
    "_typed_parameters_for_enclosing_callable",
]
