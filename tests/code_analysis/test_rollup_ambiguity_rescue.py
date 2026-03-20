# SPDX-License-Identifier: MIT

from __future__ import annotations

from sciona.code_analysis.artifacts import rollups
from sciona.code_analysis.artifacts.call_resolution import (
    _python_repeated_segment_variants,
)
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


def test_python_export_chain_rescues_no_candidates_via_package_surface_scope() -> None:
    candidate = rollups._resolve_python_export_chain_ambiguous(
        identifier="sympy.pi",
        direct_candidates=[],
        fallback_candidates=[],
        caller_module="sympy.client",
        callable_qname_by_id={
            "id_pi": "sympy.core.numbers.pi",
        },
        module_lookup={
            "id_pi": "sympy.core.numbers",
        },
        import_targets={
            "sympy.client": {"sympy"},
            "sympy": {"sympy.core"},
            "sympy.core": {"sympy.core.numbers"},
        },
        expanded_import_targets={"sympy.client": {"sympy"}},
        module_bindings_by_name={
            "sympy.core.numbers": {"pi"},
        },
        module_file_by_name={"sympy": "sympy/__init__.py"},
    )
    assert candidate == "id_pi"


def test_python_export_chain_rescues_constructor_owner_terminal_match() -> None:
    candidate = rollups._resolve_python_export_chain_ambiguous(
        identifier="sympy.Add",
        direct_candidates=["id_add_new"],
        fallback_candidates=[],
        caller_module="sympy.parsing.latex.transformer",
        callable_qname_by_id={
            "id_add_new": "sympy.core.add.Add.__new__",
        },
        module_lookup={
            "id_add_new": "sympy.core.add",
        },
        import_targets={
            "sympy.parsing.latex.transformer": {"sympy"},
            "sympy": {"sympy.core"},
            "sympy.core": {"sympy.core.add"},
        },
        expanded_import_targets={"sympy.parsing.latex.transformer": {"sympy"}},
        module_bindings_by_name={
            "sympy.core.add": {"Add", "__new__"},
        },
        module_file_by_name={"sympy": "sympy/__init__.py"},
    )
    assert candidate == "id_add_new"


def test_module_binding_index_adds_constructor_owner_binding() -> None:
    bindings = rollups._build_module_binding_index(
        callable_qname_by_id={"id_add_new": "sympy.core.add.Add.__new__"},
        module_lookup={"id_add_new": "sympy.core.add"},
    )
    assert bindings["sympy.core.add"] >= {"Add", "__new__"}


def test_python_repeated_segment_variants_collapses_adjacent_duplicate_module() -> None:
    variants = _python_repeated_segment_variants("sympy.sets.sets.Set")
    assert "sympy.sets.Set" in variants


def test_resolve_callees_rescues_python_repeated_segment_identifier() -> None:
    resolved_ids, _resolved_names, _stats, callsite_rows = rollups._resolve_callees(
        ("sympy.sets.sets.Set",),
        {
            "sympy.sets.Set": ["id_set_new"],
            "Set": ["id_set_new"],
        },
        caller_module="sympy.tests.foo",
        caller_language="python",
        module_lookup={
            "id_set_new": "sympy.sets",
        },
        callable_qname_by_id={
            "id_set_new": "sympy.sets.Set.__new__",
        },
        import_targets={
            "sympy.tests.foo": {"sympy"},
            "sympy": {"sympy.sets"},
        },
        expanded_import_targets={"sympy.tests.foo": {"sympy"}},
        module_ancestors={"sympy.tests.foo": {"sympy.tests", "sympy"}},
        module_bindings_by_name={"sympy.sets": {"Set", "__new__"}},
        module_file_by_name={"sympy": "sympy/__init__.py"},
        ts_barrel_export_map={},
        js_barrel_export_map={},
        rejected_observations=[],
        local_binding_facts=(),
    )
    assert resolved_ids == {"id_set_new"}
    assert any(row[1] == "accepted" and row[2] == "id_set_new" for row in callsite_rows)


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
        js_barrel_export_map={},
        simple_identifier=rollups._simple_identifier,
        module_in_scope=rollups._module_in_scope,
        best_candidate_by_module_distance=rollups._best_candidate_by_module_distance,
        allow_distance_fallback=False,
    )
    assert candidate == "id_bold"


def test_javascript_structural_rescue_infers_index_barrel_candidates_from_identifier() -> None:
    candidate = resolve_javascript_structural_ambiguous(
        identifier="nodebb.src.user.index.getUsersFields",
        direct_candidates=[],
        fallback_candidates=[],
        caller_module="nodebb.src.topics.fork",
        callable_qname_by_id={
            "id_getUsersFields": "nodebb.src.user.data.getUsersFields",
            "id_getSettings": "nodebb.src.user.data.getSettings",
        },
        module_lookup={
            "id_getUsersFields": "nodebb.src.user.data",
            "id_getSettings": "nodebb.src.user.data",
        },
        import_targets={"nodebb.src.topics.fork": {"nodebb.src.user.index"}},
        expanded_import_targets={"nodebb.src.topics.fork": {"nodebb.src.user.index"}},
        js_barrel_export_map={"nodebb.src.topics.fork": {"nodebb.src.user.data"}},
        simple_identifier=rollups._simple_identifier,
        module_in_scope=rollups._module_in_scope,
        best_candidate_by_module_distance=rollups._best_candidate_by_module_distance,
        allow_distance_fallback=False,
    )
    assert candidate == "id_getUsersFields"


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


def test_python_export_scope_includes_ancestor_import_surfaces() -> None:
    scope = rollups._python_export_scope_modules(
        caller_module="pkg.api.client.handlers",
        import_targets={
            "pkg.api.client.handlers": {"pkg.api.client.runtime"},
            "pkg.api": {"pkg.internal.exports"},
            "pkg.internal.exports": {"pkg.internal.impl"},
        },
        expanded_import_targets={
            "pkg.api.client.handlers": {"pkg.api.client.runtime"},
            "pkg.api": {"pkg.internal.exports"},
        },
        module_file_by_name={"pkg.api": "pkg/api/__init__.py"},
    )
    assert "pkg.internal.exports" in scope
    assert "pkg.internal.impl" in scope


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


def test_javascript_barrel_export_map_builds_from_index_modules() -> None:
    barrel_map = rollups._build_javascript_barrel_export_map(
        import_targets={
            "nodebb.src.topics.fork": {"nodebb.src.user.index"},
            "nodebb.src.user.index": {"nodebb.src.user.data"},
            "nodebb.src.user.data": set(),
        },
        module_bindings_by_name={
            "nodebb.src.user.index": {"getUsersFields"},
            "nodebb.src.user.data": {"getUsersFields", "getSettings"},
        },
        module_file_by_name={
            "nodebb.src.user.index": "src/user/index.js",
            "nodebb.src.user.data": "src/user/data.js",
        },
    )
    assert barrel_map["nodebb.src.topics.fork"] == {"nodebb.src.user.data"}
