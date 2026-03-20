# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared tree-sitter query surfaces for extraction."""

from __future__ import annotations

from ....contracts.declarative.loader import load_contract_json

_QUERY_SURFACES = load_contract_json("query_surfaces.json")


def _surface(language: str, key: str) -> tuple[str, ...] | frozenset[str]:
    values = _QUERY_SURFACES[language][key]
    if key in {"calls", "skip_calls", "structural_nodes", "structural_carriers"}:
        return frozenset(values)
    return tuple(values)


# Import query surfaces.
PYTHON_IMPORT_NODE_TYPES = _surface("python", "imports")
TYPESCRIPT_IMPORT_EXPORT_NODE_TYPES = _surface("typescript", "imports")
TYPESCRIPT_REQUIRE_DECLARATION_NODE_TYPES = _surface("typescript", "require_declarations")
TYPESCRIPT_DYNAMIC_IMPORT_NODE_TYPES = _surface("typescript", "dynamic_imports")
TYPESCRIPT_STRING_NODE_TYPES = _surface("typescript", "string_nodes")
JAVASCRIPT_IMPORT_EXPORT_NODE_TYPES = _surface("javascript", "imports")
JAVASCRIPT_REQUIRE_DECLARATION_NODE_TYPES = _surface("javascript", "require_declarations")
JAVASCRIPT_DYNAMIC_IMPORT_NODE_TYPES = _surface("javascript", "dynamic_imports")
JAVA_PACKAGE_NODE_TYPES = _surface("java", "packages")
JAVA_IMPORT_NODE_TYPES = _surface("java", "imports")

# Call query surfaces.
PYTHON_CALL_NODE_TYPES = _surface("python", "calls")
TYPESCRIPT_CALL_NODE_TYPES = _surface("typescript", "calls")
JAVA_CALL_NODE_TYPES = _surface("java", "calls")
JAVASCRIPT_CALL_NODE_TYPES = _surface("javascript", "calls")

# Structural extraction query surfaces.
PYTHON_STRUCTURAL_NODE_TYPES = _surface("python", "structural_nodes")
PYTHON_STRUCTURAL_CARRIER_NODE_TYPES = _surface("python", "structural_carriers")
TYPESCRIPT_STRUCTURAL_NODE_TYPES = _surface("typescript", "structural_nodes")
TYPESCRIPT_STRUCTURAL_CARRIER_NODE_TYPES = _surface("typescript", "structural_carriers")
JAVA_STRUCTURAL_NODE_TYPES = _surface("java", "structural_nodes")
JAVA_STRUCTURAL_CARRIER_NODE_TYPES = _surface("java", "structural_carriers")
JAVASCRIPT_STRUCTURAL_NODE_TYPES = _surface("javascript", "structural_nodes")
JAVASCRIPT_STRUCTURAL_CARRIER_NODE_TYPES = _surface("javascript", "structural_carriers")

# Nested structural nodes where calls should not escape caller attribution.
PYTHON_SKIP_CALL_NODE_TYPES = _surface("python", "skip_calls")
TYPESCRIPT_SKIP_CALL_NODE_TYPES = _surface("typescript", "skip_calls")
JAVA_SKIP_CALL_NODE_TYPES = _surface("java", "skip_calls")
JAVASCRIPT_SKIP_CALL_NODE_TYPES = _surface("javascript", "skip_calls")
