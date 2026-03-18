# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Text and type helpers for JavaScript extraction."""

from __future__ import annotations


def function_body_node(node) -> object | None:
    if node is None:
        return None
    return node.child_by_field_name("body") or node


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    text = getattr(node, "text", None)
    if text:
        return text.decode("utf-8")
    return content[node.start_byte : node.end_byte].decode("utf-8")


def name_chain(node, content: bytes) -> tuple[str, ...]:
    if node is None:
        return ()
    if node.type in {"identifier", "property_identifier", "type_identifier"}:
        value = node_text(node, content)
        return (value,) if value else ()
    if node.type in {"member_expression", "subscript_expression"}:
        object_node = node.child_by_field_name("object")
        property_node = node.child_by_field_name("property")
        left = name_chain(object_node, content)
        right = name_chain(property_node, content)
        return (*left, *right)
    if node.type == "this":
        return ("this",)
    if node.type == "super":
        return ("super",)
    named = getattr(node, "named_children", [])
    if len(named) == 1:
        return name_chain(named[0], content)
    return ()


def parse_type_annotation(node, content: bytes) -> tuple[str, ...]:
    if node is None:
        return ()
    if node.type == "generic_type":
        type_args = node.child_by_field_name("type_arguments")
        if type_args is not None:
            for child in getattr(type_args, "named_children", []):
                nested = parse_type_annotation(child, content)
                if nested:
                    return nested
    chain = name_chain(node, content)
    if chain:
        return chain
    for child in getattr(node, "named_children", []):
        nested = parse_type_annotation(child, content)
        if nested:
            return nested
    return ()


def typed_constructor_parameters(
    node,
    content: bytes,
) -> list[tuple[str, tuple[str, ...]]]:
    params = node.child_by_field_name("parameters")
    if params is None:
        return []
    typed: list[tuple[str, tuple[str, ...]]] = []
    for child in getattr(params, "children", []):
        if child.type not in {"required_parameter", "optional_parameter"}:
            continue
        name_node = child.child_by_field_name("pattern") or child.child_by_field_name(
            "name"
        )
        if name_node is None:
            name_node = next(
                (c for c in getattr(child, "children", []) if c.type == "identifier"),
                None,
            )
        type_node = child.child_by_field_name("type")
        name = node_text(name_node, content) if name_node else None
        type_chain = parse_type_annotation(type_node, content)
        if name and type_chain:
            typed.append((name, type_chain))
    return typed


__all__ = [
    "function_body_node",
    "name_chain",
    "node_text",
    "parse_type_annotation",
    "typed_constructor_parameters",
]
