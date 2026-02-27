# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared tree-sitter query surfaces for extraction."""

from __future__ import annotations

# Import query surfaces.
PYTHON_IMPORT_NODE_TYPES = ("import_statement", "import_from_statement")
TYPESCRIPT_IMPORT_EXPORT_NODE_TYPES = (
    "import_statement",
    "export_statement",
)
TYPESCRIPT_REQUIRE_DECLARATION_NODE_TYPES = ("lexical_declaration",)
TYPESCRIPT_STRING_NODE_TYPES = ("string",)
JAVA_PACKAGE_NODE_TYPES = ("package_declaration",)
JAVA_IMPORT_NODE_TYPES = ("import_declaration",)

# Call query surfaces.
PYTHON_CALL_NODE_TYPES = frozenset({"call"})
TYPESCRIPT_CALL_NODE_TYPES = frozenset({"call_expression", "new_expression"})
JAVA_CALL_NODE_TYPES = frozenset(
    {"method_invocation", "object_creation_expression", "explicit_constructor_invocation"}
)

# Structural extraction query surfaces.
PYTHON_STRUCTURAL_NODE_TYPES = frozenset(
    {
        "decorated_definition",
        "class_definition",
        "function_definition",
        "assignment",
        "augmented_assignment",
    }
)
TYPESCRIPT_STRUCTURAL_NODE_TYPES = frozenset(
    {
        "class_declaration",
        "abstract_class_declaration",
        "interface_declaration",
        "function_declaration",
        "method_definition",
        "method_signature",
        "abstract_method_signature",
        "variable_declarator",
        "public_field_definition",
        "private_field_definition",
        "property_definition",
        "field_definition",
        "assignment_expression",
    }
)
JAVA_STRUCTURAL_NODE_TYPES = frozenset(
    {
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "record_declaration",
        "method_declaration",
        "constructor_declaration",
        "compact_constructor_declaration",
        "field_declaration",
    }
)

# Nested structural nodes where calls should not escape caller attribution.
PYTHON_SKIP_CALL_NODE_TYPES = frozenset({"class_definition"})
TYPESCRIPT_SKIP_CALL_NODE_TYPES = frozenset(
    {"class_declaration", "abstract_class_declaration", "class", "class_expression"}
)
JAVA_SKIP_CALL_NODE_TYPES = frozenset(
    {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}
)
