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
PYTHON_PROFILE_DECORATOR_NODE_TYPES = ("decorator",)

TYPESCRIPT_PROFILE_FUNCTION_NODE_TYPES = (
    "function_declaration",
    "method_definition",
    "method_signature",
    "abstract_method_signature",
)
TYPESCRIPT_PROFILE_CLASS_NODE_TYPES = ("class_declaration",)
TYPESCRIPT_PROFILE_PARAMETER_NODE_TYPES = (
    "required_parameter",
    "optional_parameter",
)
TYPESCRIPT_PROFILE_BASE_NODE_TYPES = ("identifier", "type_identifier")
TYPESCRIPT_PROFILE_DECORATOR_NODE_TYPES = ("decorator",)

JAVA_PROFILE_FUNCTION_NODE_TYPES = ("method_declaration", "constructor_declaration")
JAVA_PROFILE_CLASS_NODE_TYPES = ("class_declaration",)
JAVA_PROFILE_PARAMETER_NODE_TYPES = ("formal_parameter",)
JAVA_PROFILE_BASE_NODE_TYPES = ("type_identifier", "identifier", "scoped_type_identifier")
JAVA_PROFILE_DECORATOR_NODE_TYPES = ("annotation", "marker_annotation")
