# SPDX-License-Identifier: MIT

from __future__ import annotations

from sciona.code_analysis.artifacts import rollups


def test_python_export_chain_ambiguity_rescue_picks_terminal_match() -> None:
    candidate = rollups._resolve_python_export_chain_ambiguous(
        identifier="sin",
        direct_candidates=["id_sin_a", "id_cos", "id_sin_b"],
        fallback_candidates=[],
        caller_module="sympy.physics.mechanics",
        callable_qname_by_id={
            "id_sin_a": "sympy.functions.elementary.trigonometric.sin",
            "id_sin_b": "sympy.functions.special.sin",
            "id_cos": "sympy.functions.elementary.trigonometric.cos",
        },
        module_lookup={
            "id_sin_a": "sympy.functions.elementary.trigonometric",
            "id_sin_b": "sympy.functions.special",
            "id_cos": "sympy.functions.elementary.trigonometric",
        },
        import_targets={"sympy.physics.mechanics": {"sympy"}},
        expanded_import_targets={"sympy.physics.mechanics": {"sympy"}},
    )
    assert candidate == "id_sin_b"


def test_typescript_barrel_ambiguity_rescue_prefers_closest_module() -> None:
    candidate = rollups._resolve_typescript_barrel_ambiguous(
        identifier="create",
        direct_candidates=["id_far", "id_near"],
        fallback_candidates=[],
        caller_module="app.feature.user",
        callable_qname_by_id={
            "id_far": "app.shared.utils.factory.create",
            "id_near": "app.feature.user.index.create",
        },
        module_lookup={
            "id_far": "app.shared.utils.factory",
            "id_near": "app.feature.user.index",
        },
        import_targets={
            "app.feature.user": {"app.feature"},
            "app.feature": {"app.feature.user.index"},
        },
        expanded_import_targets={"app.feature.user": {"app.feature", "app.feature.user.index"}},
    )
    assert candidate == "id_near"
