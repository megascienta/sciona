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
                "emits_nodes": ["classifier"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "query_access": {"mode": "direct"},
            },
            {
                "construct": "function_declaration",
                "node_types": ["function_definition", "async_function_definition"],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "query_access": {"mode": "direct"},
            },
            {
                "construct": "bound_callable_declaration",
                "node_types": ["assignment", "augmented_assignment"],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "constraints": ["rhs must be lambda with stable lexical binding"],
                "query_access": {"mode": "direct"},
            },
            {
                "construct": "decorated_definition_unwrap",
                "node_types": ["decorated_definition"],
                "emits_nodes": [],
                "emits_edges": [],
                "query_access": {"mode": "direct"},
            },
            {
                "construct": "local_inheritance_edges",
                "node_types": ["class_definition"],
                "emits_nodes": [],
                "emits_edges": ["EXTENDS"],
                "constraints": ["syntax-local base references only"],
                "query_access": {"mode": "direct"},
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
                "emits_nodes": ["classifier"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "query_access": {"mode": "direct"},
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
                "query_access": {"mode": "direct"},
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
                "emits_nodes": ["classifier", "callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "constraints": [
                    "function/method emission for stable lexical bindings, including nested bound expressions, object-literal bound methods, class member fields, and anonymous export default callables; inline anonymous callbacks are non-structural"
                ],
                "query_access": {
                    "mode": "nested",
                    "anchors": [
                        "assignment_expression",
                        "class_body",
                        "expression_statement",
                        "export_statement",
                        "lexical_declaration",
                        "public_field_definition",
                        "statement_block",
                        "variable_declarator",
                    ],
                },
            },
            {
                "construct": "instance_and_alias_tracking",
                "node_types": ["new_expression", "assignment_expression", "variable_declarator"],
                "emits_nodes": [],
                "emits_edges": [],
                "query_access": {
                    "mode": "nested",
                    "anchors": [
                        "assignment_expression",
                        "class_body",
                        "expression_statement",
                        "lexical_declaration",
                        "public_field_definition",
                        "statement_block",
                        "variable_declarator",
                    ],
                },
            },
            {
                "construct": "local_inheritance_edges",
                "node_types": ["class_declaration", "class_expression", "interface_declaration"],
                "emits_nodes": [],
                "emits_edges": ["EXTENDS", "IMPLEMENTS"],
                "constraints": ["syntax-local base/interface references only"],
                "query_access": {
                    "mode": "nested",
                    "anchors": [
                        "abstract_class_declaration",
                        "assignment_expression",
                        "class_declaration",
                        "export_statement",
                        "interface_declaration",
                        "public_field_definition",
                        "variable_declarator",
                    ],
                },
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
                "emits_nodes": ["classifier"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "query_access": {"mode": "direct"},
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
                "query_access": {"mode": "direct"},
            },
            {
                "construct": "field_type_tracking",
                "node_types": ["field_declaration"],
                "emits_nodes": [],
                "emits_edges": [],
                "query_access": {"mode": "direct"},
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
                "query_access": {"mode": "direct"},
            },
        ],
        "javascript": [
            {
                "construct": "class_declaration",
                "node_types": ["class_declaration", "class_expression"],
                "emits_nodes": ["classifier"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "query_access": {
                    "mode": "nested",
                    "anchors": [
                        "assignment_expression",
                        "class_declaration",
                        "export_statement",
                        "field_definition",
                        "variable_declarator",
                    ],
                },
            },
            {
                "construct": "callable_declaration",
                "node_types": ["function_declaration", "method_definition"],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "query_access": {"mode": "direct"},
            },
            {
                "construct": "bound_callable_declaration",
                "node_types": ["variable_declarator", "assignment_expression", "field_definition"],
                "emits_nodes": ["callable"],
                "emits_edges": ["LEXICALLY_CONTAINS"],
                "constraints": [
                    "function/arrow callable promoted only for stable lexical bindings; inline anonymous callbacks are non-structural"
                ],
                "query_access": {"mode": "direct"},
            },
            {
                "construct": "local_inheritance_edges",
                "node_types": ["class_declaration", "class_expression"],
                "emits_nodes": [],
                "emits_edges": ["EXTENDS"],
                "constraints": ["syntax-local base references only"],
                "query_access": {
                    "mode": "nested",
                    "anchors": [
                        "assignment_expression",
                        "class_declaration",
                        "export_statement",
                        "field_definition",
                        "variable_declarator",
                    ],
                },
            },
        ],
    }
