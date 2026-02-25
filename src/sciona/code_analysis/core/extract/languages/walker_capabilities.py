# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Declarative walker capability map by language."""

from __future__ import annotations


def build_walker_capabilities() -> dict[str, list[dict[str, object]]]:
    """Return per-language construct coverage mapped to structural emissions."""
    return {
        "python": [
            {
                "construct": "class_declaration",
                "node_types": ["class_definition"],
                "emits_nodes": ["class"],
                "emits_edges": ["CONTAINS"],
            },
            {
                "construct": "function_declaration",
                "node_types": ["function_definition", "async_function_definition"],
                "emits_nodes": ["function", "method"],
                "emits_edges": ["CONTAINS", "DEFINES_METHOD"],
            },
            {
                "construct": "decorated_definition_unwrap",
                "node_types": ["decorated_definition"],
                "emits_nodes": [],
                "emits_edges": [],
            },
        ],
        "typescript": [
            {
                "construct": "class_like_declaration",
                "node_types": [
                    "class_declaration",
                    "abstract_class_declaration",
                    "interface_declaration",
                ],
                "emits_nodes": ["class"],
                "emits_edges": ["CONTAINS"],
            },
            {
                "construct": "callable_declaration",
                "node_types": [
                    "function_declaration",
                    "method_definition",
                    "method_signature",
                    "abstract_method_signature",
                ],
                "emits_nodes": ["function", "method"],
                "emits_edges": ["CONTAINS", "DEFINES_METHOD"],
            },
            {
                "construct": "class_and_function_expressions",
                "node_types": [
                    "class",
                    "class_expression",
                    "arrow_function",
                    "function_expression",
                ],
                "emits_nodes": ["class", "function", "method"],
                "emits_edges": ["CONTAINS", "DEFINES_METHOD"],
            },
            {
                "construct": "instance_and_alias_tracking",
                "node_types": ["new_expression", "assignment_expression", "variable_declarator"],
                "emits_nodes": [],
                "emits_edges": [],
            },
        ],
        "java": [
            {
                "construct": "class_like_declaration",
                "node_types": [
                    "class_declaration",
                    "interface_declaration",
                    "enum_declaration",
                    "record_declaration",
                ],
                "emits_nodes": ["class"],
                "emits_edges": ["CONTAINS"],
            },
            {
                "construct": "method_like_declaration",
                "node_types": [
                    "method_declaration",
                    "constructor_declaration",
                    "compact_constructor_declaration",
                ],
                "emits_nodes": ["method"],
                "emits_edges": ["DEFINES_METHOD"],
            },
            {
                "construct": "field_type_tracking",
                "node_types": ["field_declaration"],
                "emits_nodes": [],
                "emits_edges": [],
            },
        ],
    }

