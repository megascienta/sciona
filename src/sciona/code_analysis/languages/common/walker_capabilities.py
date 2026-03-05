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
                "emits_nodes": ["type"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
            },
            {
                "construct": "function_declaration",
                "node_types": ["function_definition", "async_function_definition"],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
            },
            {
                "construct": "bound_callable_declaration",
                "node_types": ["assignment", "augmented_assignment"],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "constraints": ["rhs must be lambda with stable lexical binding"],
            },
            {
                "construct": "decorated_definition_unwrap",
                "node_types": ["decorated_definition"],
                "emits_nodes": [],
                "emits_edges": [],
            },
            {
                "construct": "local_inheritance_edges",
                "node_types": ["class_definition"],
                "emits_nodes": [],
                "emits_edges": ["EXTENDS"],
                "constraints": ["syntax-local base references only"],
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
                "emits_nodes": ["type"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
            },
            {
                "construct": "callable_declaration",
                "node_types": [
                    "function_declaration",
                    "method_definition",
                    "method_signature",
                    "abstract_method_signature",
                ],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
            },
            {
                "construct": "class_and_function_expressions",
                "node_types": [
                    "export_statement",
                    "class",
                    "class_expression",
                    "object",
                    "pair",
                    "method_definition",
                    "arrow_function",
                    "function_expression",
                ],
                "emits_nodes": ["type", "callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "constraints": [
                    "function/method emission for stable lexical bindings, including nested bound expressions, object-literal bound methods, class member fields, and anonymous export default callables; inline anonymous callbacks are non-structural"
                ],
            },
            {
                "construct": "instance_and_alias_tracking",
                "node_types": ["new_expression", "assignment_expression", "variable_declarator"],
                "emits_nodes": [],
                "emits_edges": [],
            },
            {
                "construct": "local_inheritance_edges",
                "node_types": ["class_declaration", "class_expression", "interface_declaration"],
                "emits_nodes": [],
                "emits_edges": ["EXTENDS", "IMPLEMENTS"],
                "constraints": ["syntax-local base/interface references only"],
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
                "emits_nodes": ["type"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
            },
            {
                "construct": "method_like_declaration",
                "node_types": [
                    "method_declaration",
                    "constructor_declaration",
                    "compact_constructor_declaration",
                ],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
            },
            {
                "construct": "field_type_tracking",
                "node_types": ["field_declaration"],
                "emits_nodes": [],
                "emits_edges": [],
            },
            {
                "construct": "local_inheritance_edges",
                "node_types": [
                    "class_declaration",
                    "interface_declaration",
                    "enum_declaration",
                    "record_declaration",
                ],
                "emits_nodes": [],
                "emits_edges": ["EXTENDS", "IMPLEMENTS"],
                "constraints": ["syntax-local base/interface references only"],
            },
        ],
        "javascript": [
            {
                "construct": "class_declaration",
                "node_types": ["class_declaration", "class_expression"],
                "emits_nodes": ["type"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
            },
            {
                "construct": "callable_declaration",
                "node_types": ["function_declaration", "method_definition"],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
            },
            {
                "construct": "bound_callable_declaration",
                "node_types": ["variable_declarator", "assignment_expression", "field_definition"],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "constraints": [
                    "function/arrow callable promoted only for stable lexical bindings; inline anonymous callbacks are non-structural"
                ],
            },
            {
                "construct": "local_inheritance_edges",
                "node_types": ["class_declaration", "class_expression"],
                "emits_nodes": [],
                "emits_edges": ["EXTENDS"],
                "constraints": ["syntax-local base references only"],
            },
        ],
    }
