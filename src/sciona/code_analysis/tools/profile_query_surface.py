# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared tree-sitter query surfaces for profile introspection."""

from __future__ import annotations

PYTHON_PROFILE_FUNCTION_NODE_TYPES = (
    "function_definition",
    "async_function_definition",
)
PYTHON_PROFILE_CLASS_NODE_TYPES = ("class_definition",)
PYTHON_PROFILE_PARAMETER_NODE_TYPES = (
    "identifier",
    "default_parameter",
    "typed_parameter",
    "typed_default_parameter",
    "list_splat_pattern",
    "dictionary_splat_pattern",
)
PYTHON_PROFILE_BASE_NODE_TYPES = ("identifier", "attribute")

TYPESCRIPT_PROFILE_FUNCTION_NODE_TYPES = (
    "function_declaration",
    "method_definition",
    "method_signature",
    "abstract_method_signature",
)
TYPESCRIPT_PROFILE_CLASS_NODE_TYPES = (
    "class_declaration",
    "abstract_class_declaration",
    "class_expression",
)
TYPESCRIPT_PROFILE_PARAMETER_NODE_TYPES = (
    "required_parameter",
    "optional_parameter",
)
TYPESCRIPT_PROFILE_BASE_NODE_TYPES = ("identifier", "type_identifier")

JAVASCRIPT_PROFILE_FUNCTION_NODE_TYPES = (
    "function_declaration",
    "method_definition",
)
JAVASCRIPT_PROFILE_CLASS_NODE_TYPES = (
    "class_declaration",
    "class_expression",
)
JAVASCRIPT_PROFILE_PARAMETER_NODE_TYPES = (
    "identifier",
    "assignment_pattern",
    "rest_pattern",
)
JAVASCRIPT_PROFILE_BASE_NODE_TYPES = ("identifier",)

JAVA_PROFILE_FUNCTION_NODE_TYPES = (
    "method_declaration",
    "constructor_declaration",
    "compact_constructor_declaration",
)
JAVA_PROFILE_CLASS_NODE_TYPES = (
    "class_declaration",
    "interface_declaration",
    "enum_declaration",
    "record_declaration",
)
JAVA_PROFILE_PARAMETER_NODE_TYPES = ("formal_parameter",)
JAVA_PROFILE_BASE_NODE_TYPES = ("type_identifier", "identifier", "scoped_type_identifier")
