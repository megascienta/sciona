# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Executable language-parity contract for code-analysis."""

from __future__ import annotations


PARITY_CONTRACT_VERSION = 7


def build_parity_contract() -> dict[str, object]:
    """Return a machine-readable parity contract for builtin languages."""
    return {
        "version": PARITY_CONTRACT_VERSION,
        "languages": ["java", "javascript", "python", "typescript"],
        "objective": "structural_contract_capability_parity",
        "dimensions": {
            "structural_nodes_edges_contract": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "lexical_contains_edges": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "core_extends_edges": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "core_implements_edges": {
                "java": "yes",
                "javascript": "n/a",
                "python": "n/a",
                "typescript": "yes",
            },
            "imports_declared_and_aliasing": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "normalized_import_model_convergence": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "call_extraction_and_attribution": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "walker_construct_capability_declarations": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "callable_role_coverage": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "parse_diagnostics_and_degraded_analysis": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "profile_function_extras_tree_sitter": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
            "profile_classifier_extras_tree_sitter": {
                "java": "yes",
                "javascript": "yes",
                "python": "yes",
                "typescript": "yes",
            },
        },
        "required_resolution_stages": [
            "receiver_typed_or_instance_mapped",
            "import_or_member_alias_narrowing",
            "classifier_scoped_fallback",
            "module_scoped_fallback",
        ],
        "resolution_stage_enforcement": {
            "owner": "language_adapters_via_shared_kernel",
            "strict_call_gate_role": "final_materialization_only",
        },
        "documented_asymmetries": {
            "python": {
                "implements_edges": {
                    "present": False,
                    "reason": "python has no dedicated interface-implementation syntax token",
                },
            },
            "java": {
                "callable_types": ["callable"],
                "reason": "java emits callable nodes only; no module-level function declarations",
                "async_callable_kind": {
                    "present": False,
                    "reason": "java extraction does not model async/await callable kind metadata",
                },
            },
            "javascript": {
                "implements_edges": {
                    "present": False,
                    "reason": "javascript has no dedicated interface-implementation syntax token",
                },
            },
        },
    }
