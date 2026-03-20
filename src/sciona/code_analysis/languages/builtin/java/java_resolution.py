# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java variable/type resolution utilities."""

from __future__ import annotations

from ....core.normalize_model import FileSnapshot
from ...common.helpers.shared import node_text
from ....core.extract.parsing.query_helpers import find_nodes_of_types_query
from ...common.ir.symbol_ir import TypedSymbolBinding


def collect_parameter_types(
    node,
    snapshot: FileSnapshot,
) -> dict[str, str]:
    if node is None:
        return {}
    collected: dict[str, str] = {}
    for param in find_nodes_of_types_query(
        node,
        language_name="java",
        node_types=("formal_parameter",),
    ):
        type_node = param.child_by_field_name("type")
        name_node = param.child_by_field_name("name")
        type_text = node_text(type_node, snapshot.content) if type_node else None
        name = node_text(name_node, snapshot.content) if name_node else None
        if type_text and name:
            collected[name] = type_text
    return collected


def collect_declared_vars(
    node,
    snapshot: FileSnapshot,
) -> list[tuple[str, str]]:
    type_node = node.child_by_field_name("type") if node is not None else None
    type_text = node_text(type_node, snapshot.content) if type_node else None
    if not type_text:
        return []
    declared: list[tuple[str, str]] = []
    for decl in find_nodes_of_types_query(
        node,
        language_name="java",
        node_types=("variable_declarator",),
    ):
        name_node = decl.child_by_field_name("name")
        name = node_text(name_node, snapshot.content)
        if name:
            declared.append((name, type_text))
    return declared


def collect_local_var_types(
    body_node,
    snapshot: FileSnapshot,
) -> dict[str, str]:
    if body_node is None:
        return {}
    collected: dict[str, str] = {}
    nodes = find_nodes_of_types_query(
        body_node,
        language_name="java",
        node_types=(
            "local_variable_declaration",
            "enhanced_for_statement",
            "catch_formal_parameter",
            "instanceof_expression",
        ),
    )
    for node in nodes:
        if node.type == "local_variable_declaration":
            for name, type_text in collect_declared_vars(node, snapshot):
                collected[name] = type_text
            continue
        if node.type == "enhanced_for_statement":
            type_node = node.child_by_field_name("type")
            name_node = node.child_by_field_name("name")
            type_text = node_text(type_node, snapshot.content) if type_node else None
            name = node_text(name_node, snapshot.content) if name_node else None
            if type_text and name:
                collected[name] = type_text
            continue
        if node.type == "catch_formal_parameter":
            type_node = node.child_by_field_name("type")
            if type_node is None:
                type_node = next(
                    (
                        child
                        for child in getattr(node, "named_children", [])
                        if child.type == "catch_type"
                    ),
                    None,
                )
            name_node = node.child_by_field_name("name")
            type_text = node_text(type_node, snapshot.content) if type_node else None
            name = node_text(name_node, snapshot.content) if name_node else None
            if type_text and name:
                collected[name] = type_text
            continue
        if node.type == "instanceof_expression":
            type_node = node.child_by_field_name("right")
            name_node = node.child_by_field_name("name")
            type_text = node_text(type_node, snapshot.content) if type_node else None
            name = node_text(name_node, snapshot.content) if name_node else None
            if type_text and name:
                collected[name] = type_text
    return collected


def collect_local_bindings(
    body_node,
    snapshot: FileSnapshot,
) -> list[TypedSymbolBinding]:
    return [
        TypedSymbolBinding(symbol=name, target_type=type_name, source="java_local")
        for name, type_name in collect_local_var_types(body_node, snapshot).items()
    ]


def collect_constructor_field_types(
    body_node,
    snapshot: FileSnapshot,
    *,
    available_types: dict[str, str] | None = None,
) -> dict[str, str]:
    if body_node is None:
        return {}
    available_types = available_types or {}
    collected: dict[str, str] = {}
    assignments = find_nodes_of_types_query(
        body_node,
        language_name="java",
        node_types=("assignment_expression",),
    )
    for node in assignments:
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if left is None or right is None:
            continue
        type_text = None
        if right.type == "object_creation_expression":
            type_node = right.child_by_field_name("type")
            type_text = node_text(type_node, snapshot.content) if type_node else None
        elif right.type == "identifier":
            rhs_name = node_text(right, snapshot.content)
            if rhs_name:
                type_text = available_types.get(rhs_name)
        if not type_text:
            continue
        field_name = None
        if left.type == "field_access":
            object_node = left.child_by_field_name("object")
            field_node = left.child_by_field_name("field") or left.child_by_field_name("name")
            object_text = node_text(object_node, snapshot.content) if object_node else None
            if object_text == "this":
                field_name = node_text(field_node, snapshot.content) if field_node else None
        if field_name is None:
            left_text = node_text(left, snapshot.content) or ""
            if left_text.startswith("this.") and "." in left_text:
                field_name = left_text.split(".", 1)[1].strip()
        if field_name:
            collected[field_name] = type_text
    return collected


def strip_type_decorations(type_text: str) -> str:
    text = type_text.strip()
    if "<" in text:
        text = text.split("<", 1)[0]
    text = text.replace("[]", "").strip()
    if " " in text:
        text = text.split()[-1]
    return text


def qualify_java_type(
    type_text: str,
    module_name: str,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    module_prefix: str | None,
    *,
    class_path_candidates: dict[str, set[str]] | None = None,
) -> str | None:
    base = strip_type_decorations(type_text)
    if not base:
        return None
    path_candidates = (class_path_candidates or {}).get(base) or set()
    if len(path_candidates) == 1:
        return next(iter(path_candidates))
    if len(path_candidates) > 1:
        return None
    class_candidates = class_name_candidates.get(base) or set()
    if len(class_candidates) == 1:
        return next(iter(class_candidates))
    if len(class_candidates) > 1:
        return None
    if base in import_aliases:
        return import_aliases[base]
    return None
