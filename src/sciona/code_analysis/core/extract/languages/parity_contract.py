# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Executable language-parity contract for code-analysis."""

from __future__ import annotations


PARITY_CONTRACT_VERSION = 1


def build_parity_contract() -> dict[str, object]:
    """Return a machine-readable parity contract for PY/TS/Java."""
    return {
        "version": PARITY_CONTRACT_VERSION,
        "languages": ["java", "python", "typescript"],
        "objective": "full_factual_parity_depth_quality",
        "dimensions": {
            "structural_nodes_edges_contract": {
                "java": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "imports_declared_and_aliasing": {
                "java": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "normalized_import_model_convergence": {
                "java": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "call_extraction_and_attribution": {
                "java": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "walker_construct_capability_declarations": {
                "java": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "profile_function_extras_tree_sitter": {
                "java": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "profile_class_extras_tree_sitter": {
                "java": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "profile_decorators_tree_sitter": {
                "java": "yes",
                "python": "yes",
                "typescript": "yes",
            },
        },
        "required_resolution_stages": [
            "receiver_typed_or_instance_mapped",
            "import_or_member_alias_narrowing",
            "class_scoped_fallback",
            "module_scoped_fallback",
        ],
        "documented_asymmetries": {
            "java": {
                "callable_types": ["method"],
                "reason": "java has no module-level function declarations",
            }
        },
    }
