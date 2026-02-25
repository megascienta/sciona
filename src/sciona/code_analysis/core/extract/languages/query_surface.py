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
TYPESCRIPT_CALL_NODE_TYPES = frozenset({"call_expression"})
JAVA_CALL_NODE_TYPES = frozenset(
    {"method_invocation", "object_creation_expression", "explicit_constructor_invocation"}
)

# Nested structural nodes where calls should not escape caller attribution.
PYTHON_SKIP_CALL_NODE_TYPES = frozenset({"class_definition"})
TYPESCRIPT_SKIP_CALL_NODE_TYPES = frozenset(
    {"class_declaration", "abstract_class_declaration", "class", "class_expression"}
)
JAVA_SKIP_CALL_NODE_TYPES = frozenset(
    {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}
)
