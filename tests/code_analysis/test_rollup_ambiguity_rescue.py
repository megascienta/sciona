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
        import_targets={
            "sympy.physics.mechanics": {"sympy"},
            "sympy": {"sympy.functions.special", "sympy.functions.elementary.trigonometric"},
        },
        expanded_import_targets={"sympy.physics.mechanics": {"sympy"}},
        module_bindings_by_name={
            "sympy.functions.elementary.trigonometric": {"sin", "cos"},
            "sympy.functions.special": {"sin"},
        },
        module_file_by_name={"sympy": "sympy/__init__.py"},
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
        ts_barrel_export_map={
            "app.feature.user": {"app.feature.user.index"},
        },
    )
    assert candidate == "id_near"


def test_python_export_scope_traverses_init_chain() -> None:
    scope = rollups._python_export_scope_modules(
        caller_module="pkg.client",
        import_targets={
            "pkg.client": {"pkg"},
            "pkg": {"pkg.sub"},
            "pkg.sub": {"pkg.sub.impl"},
        },
        expanded_import_targets={"pkg.client": {"pkg"}},
        module_file_by_name={"pkg": "pkg/__init__.py"},
    )
    assert "pkg.sub" in scope
    assert "pkg.sub.impl" in scope


def test_typescript_barrel_export_map_builds_from_index_modules() -> None:
    barrel_map = rollups._build_typescript_barrel_export_map(
        import_targets={
            "app.feature.user.index": {"app.feature.user.impl"},
            "app.feature.user.impl": set(),
        },
        module_bindings_by_name={
            "app.feature.user.index": {"create"},
            "app.feature.user.impl": {"create"},
        },
        module_file_by_name={
            "app.feature.user.index": "src/feature/user/index.ts",
            "app.feature.user.impl": "src/feature/user/impl.ts",
        },
    )
    assert barrel_map["app.feature.user.index"] == {"app.feature.user.impl"}
