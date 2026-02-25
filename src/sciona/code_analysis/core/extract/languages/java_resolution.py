# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java variable/type resolution utilities."""

from __future__ import annotations

from ...normalize.model import FileSnapshot
from ..utils import find_nodes_of_type


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    return content[node.start_byte : node.end_byte].decode("utf-8")


def collect_declared_vars(
    node,
    snapshot: FileSnapshot,
) -> list[tuple[str, str]]:
    type_node = node.child_by_field_name("type") if node is not None else None
    type_text = node_text(type_node, snapshot.content) if type_node else None
    if not type_text:
        return []
    declared: list[tuple[str, str]] = []
    for decl in find_nodes_of_type(node, "variable_declarator"):
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
    for decl in find_nodes_of_type(body_node, "local_variable_declaration"):
        for name, type_text in collect_declared_vars(decl, snapshot):
            collected[name] = type_text
    for param in find_nodes_of_type(body_node, "formal_parameter"):
        type_node = param.child_by_field_name("type")
        name_node = param.child_by_field_name("name")
        type_text = node_text(type_node, snapshot.content) if type_node else None
        name = node_text(name_node, snapshot.content) if name_node else None
        if type_text and name:
            collected[name] = type_text
    for for_stmt in find_nodes_of_type(body_node, "enhanced_for_statement"):
        type_node = for_stmt.child_by_field_name("type")
        name_node = for_stmt.child_by_field_name("name")
        type_text = node_text(type_node, snapshot.content) if type_node else None
        name = node_text(name_node, snapshot.content) if name_node else None
        if type_text and name:
            collected[name] = type_text
    for catch_param in find_nodes_of_type(body_node, "catch_formal_parameter"):
        type_node = catch_param.child_by_field_name("type")
        if type_node is None:
            type_node = next(
                (
                    child
                    for child in getattr(catch_param, "children", [])
                    if child.type == "catch_type"
                ),
                None,
            )
        name_node = catch_param.child_by_field_name("name")
        type_text = node_text(type_node, snapshot.content) if type_node else None
        name = node_text(name_node, snapshot.content) if name_node else None
        if type_text and name:
            collected[name] = type_text
    for instanceof_expr in find_nodes_of_type(body_node, "instanceof_expression"):
        type_node = instanceof_expr.child_by_field_name("right")
        name_node = instanceof_expr.child_by_field_name("name")
        type_text = node_text(type_node, snapshot.content) if type_node else None
        name = node_text(name_node, snapshot.content) if name_node else None
        if type_text and name:
            collected[name] = type_text
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
    import_class_map: dict[str, str],
    module_prefix: str | None,
) -> str | None:
    base = strip_type_decorations(type_text)
    if not base:
        return None
    class_candidates = class_name_candidates.get(base) or set()
    if len(class_candidates) == 1:
        return next(iter(class_candidates))
    if len(class_candidates) > 1:
        return None
    if base in import_class_map:
        return import_class_map[base]
    if "." in base:
        return f"{module_prefix}.{base}" if module_prefix else base
    if "." in module_name:
        package = module_name.rsplit(".", 1)[0]
        return f"{package}.{base}" if package else base
    return base
