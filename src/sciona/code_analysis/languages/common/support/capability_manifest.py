# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Capability manifest for extraction/query surfaces."""

from __future__ import annotations

from . import parity_contract
from . import walker_capabilities
from ..query import query_surface
from ....tools import profile_query_surface


def build_capability_manifest() -> dict[str, object]:
    return {
        "version": 1,
        "queries": _build_query_surfaces(),
        "walker_capabilities": walker_capabilities.build_walker_capabilities(),
        "parity_contract": parity_contract.build_parity_contract(),
    }


def _build_query_surfaces() -> dict[str, dict[str, object]]:
    return {
        "python": {
            "imports": sorted(query_surface.PYTHON_IMPORT_NODE_TYPES),
            "calls": sorted(query_surface.PYTHON_CALL_NODE_TYPES),
            "skip_calls": sorted(query_surface.PYTHON_SKIP_CALL_NODE_TYPES),
            "structural_nodes": sorted(query_surface.PYTHON_STRUCTURAL_NODE_TYPES),
            "structural_carriers": sorted(
                query_surface.PYTHON_STRUCTURAL_CARRIER_NODE_TYPES
            ),
            "profile": {
                "functions": sorted(profile_query_surface.PYTHON_PROFILE_FUNCTION_NODE_TYPES),
                "classifiers": sorted(
                    profile_query_surface.PYTHON_PROFILE_CLASS_NODE_TYPES
                ),
                "parameters": sorted(profile_query_surface.PYTHON_PROFILE_PARAMETER_NODE_TYPES),
                "bases": sorted(profile_query_surface.PYTHON_PROFILE_BASE_NODE_TYPES),
            },
        },
        "typescript": {
            "imports": sorted(query_surface.TYPESCRIPT_IMPORT_EXPORT_NODE_TYPES),
            "dynamic_imports": sorted(query_surface.TYPESCRIPT_DYNAMIC_IMPORT_NODE_TYPES),
            "require_declarations": sorted(
                query_surface.TYPESCRIPT_REQUIRE_DECLARATION_NODE_TYPES
            ),
            "calls": sorted(query_surface.TYPESCRIPT_CALL_NODE_TYPES),
            "skip_calls": sorted(query_surface.TYPESCRIPT_SKIP_CALL_NODE_TYPES),
            "structural_nodes": sorted(query_surface.TYPESCRIPT_STRUCTURAL_NODE_TYPES),
            "structural_carriers": sorted(
                query_surface.TYPESCRIPT_STRUCTURAL_CARRIER_NODE_TYPES
            ),
            "profile": {
                "functions": sorted(
                    profile_query_surface.TYPESCRIPT_PROFILE_FUNCTION_NODE_TYPES
                ),
                "classifiers": sorted(
                    profile_query_surface.TYPESCRIPT_PROFILE_CLASS_NODE_TYPES
                ),
                "parameters": sorted(
                    profile_query_surface.TYPESCRIPT_PROFILE_PARAMETER_NODE_TYPES
                ),
                "bases": sorted(profile_query_surface.TYPESCRIPT_PROFILE_BASE_NODE_TYPES),
            },
        },
        "javascript": {
            "imports": sorted(query_surface.JAVASCRIPT_IMPORT_EXPORT_NODE_TYPES),
            "dynamic_imports": sorted(query_surface.JAVASCRIPT_DYNAMIC_IMPORT_NODE_TYPES),
            "require_declarations": sorted(
                query_surface.JAVASCRIPT_REQUIRE_DECLARATION_NODE_TYPES
            ),
            "calls": sorted(query_surface.JAVASCRIPT_CALL_NODE_TYPES),
            "skip_calls": sorted(query_surface.JAVASCRIPT_SKIP_CALL_NODE_TYPES),
            "structural_nodes": sorted(query_surface.JAVASCRIPT_STRUCTURAL_NODE_TYPES),
            "structural_carriers": sorted(
                query_surface.JAVASCRIPT_STRUCTURAL_CARRIER_NODE_TYPES
            ),
            "profile": {
                "functions": sorted(
                    profile_query_surface.JAVASCRIPT_PROFILE_FUNCTION_NODE_TYPES
                ),
                "classifiers": sorted(
                    profile_query_surface.JAVASCRIPT_PROFILE_CLASS_NODE_TYPES
                ),
                "parameters": sorted(
                    profile_query_surface.JAVASCRIPT_PROFILE_PARAMETER_NODE_TYPES
                ),
                "bases": sorted(profile_query_surface.JAVASCRIPT_PROFILE_BASE_NODE_TYPES),
            },
        },
        "java": {
            "packages": sorted(query_surface.JAVA_PACKAGE_NODE_TYPES),
            "imports": sorted(query_surface.JAVA_IMPORT_NODE_TYPES),
            "calls": sorted(query_surface.JAVA_CALL_NODE_TYPES),
            "skip_calls": sorted(query_surface.JAVA_SKIP_CALL_NODE_TYPES),
            "structural_nodes": sorted(query_surface.JAVA_STRUCTURAL_NODE_TYPES),
            "structural_carriers": sorted(query_surface.JAVA_STRUCTURAL_CARRIER_NODE_TYPES),
            "profile": {
                "functions": sorted(profile_query_surface.JAVA_PROFILE_FUNCTION_NODE_TYPES),
                "classifiers": sorted(
                    profile_query_surface.JAVA_PROFILE_CLASS_NODE_TYPES
                ),
                "parameters": sorted(profile_query_surface.JAVA_PROFILE_PARAMETER_NODE_TYPES),
                "bases": sorted(profile_query_surface.JAVA_PROFILE_BASE_NODE_TYPES),
            },
        },
    }
