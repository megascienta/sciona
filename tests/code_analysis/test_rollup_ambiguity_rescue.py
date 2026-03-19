# SPDX-License-Identifier: MIT

from __future__ import annotations

from sciona.code_analysis.artifacts import rollups
from sciona.code_analysis.artifacts.call_resolution_javascript import (
    resolve_javascript_structural_ambiguous,
)


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


def test_python_export_chain_rescues_unique_without_provenance_via_package_scope() -> None:
    candidate = rollups._resolve_python_export_chain_ambiguous(
        identifier="pi",
        direct_candidates=[],
        fallback_candidates=["id_pi"],
        caller_module="sympy.client",
        callable_qname_by_id={
            "id_pi": "sympy.core.numbers.pi",
        },
        module_lookup={
            "id_pi": "sympy.core.numbers",
        },
        import_targets={
            "sympy.client": {"sympy.physics.mechanics"},
            "sympy.physics.mechanics": {"sympy.core.numbers"},
        },
        expanded_import_targets={"sympy.client": {"sympy.physics.mechanics"}},
        module_bindings_by_name={
            "sympy.core.numbers": {"pi"},
        },
        module_file_by_name={"sympy.physics.mechanics": "sympy/physics/mechanics/__init__.py"},
    )
    assert candidate == "id_pi"


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


def test_typescript_barrel_rescues_unique_without_provenance_single_candidate() -> None:
    candidate = rollups._resolve_typescript_barrel_ambiguous(
        identifier="create",
        direct_candidates=[],
        fallback_candidates=["id_create"],
        caller_module="app.feature.user",
        callable_qname_by_id={
            "id_create": "app.core.factory.create",
        },
        module_lookup={
            "id_create": "app.core.factory",
        },
        import_targets={
            "app.feature.user": {"app.api"},
        },
        expanded_import_targets={"app.feature.user": {"app.api"}},
        ts_barrel_export_map={
            "app.feature.user": {"app.core.factory"},
        },
    )
    assert candidate == "id_create"


def test_javascript_structural_rescue_handles_unique_namespace_tail_match() -> None:
    candidate = resolve_javascript_structural_ambiguous(
        identifier="colors.bold",
        direct_candidates=[],
        fallback_candidates=["id_bold"],
        caller_module="app.ui",
        callable_qname_by_id={
            "id_bold": "app.lib.colors.bold",
        },
        module_lookup={
            "id_bold": "app.lib.colors",
        },
        import_targets={"app.ui": {"app.colors"}},
        expanded_import_targets={"app.ui": {"app.colors"}},
        simple_identifier=rollups._simple_identifier,
        module_in_scope=rollups._module_in_scope,
        best_candidate_by_module_distance=rollups._best_candidate_by_module_distance,
        allow_distance_fallback=False,
    )
    assert candidate == "id_bold"


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
