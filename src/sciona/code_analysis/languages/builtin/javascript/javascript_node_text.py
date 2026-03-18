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


__all__ = [
    "function_body_node",
    "name_chain",
    "node_text",
]
