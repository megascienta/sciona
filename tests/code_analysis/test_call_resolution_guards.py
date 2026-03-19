# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.languages.builtin.java.java_calls import resolve_java_calls
from sciona.code_analysis.languages.builtin.javascript.javascript_calls import (
    resolve_javascript_calls,
)
from sciona.code_analysis.languages.builtin.java.java_resolution import qualify_java_type
from sciona.code_analysis.languages.builtin.python.python_calls import (
    resolve_python_calls,
)
from sciona.code_analysis.languages.builtin.typescript.typescript_calls import (
    resolve_typescript_calls,
)
from sciona.code_analysis.languages.common.ir import LocalBindingFact
from sciona.code_analysis.tools.call_extraction import (
    CallTarget,
    QualifiedCallIR,
    ReceiverCallIR,
)


def test_python_ambiguous_class_candidate_does_not_overresolve() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
    outcome_diagnostics: dict[str, int] = {}
    resolved = resolve_python_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        raw_module_map={},
        instance_map={},
        class_name_candidates={"Service": {"repo.pkg.a.Service", "repo.pkg.b.Service"}},
        outcome_diagnostics=outcome_diagnostics,
    )
    assert resolved == []
    assert outcome_diagnostics.get("ambiguous_candidate") == 1


def test_typescript_ambiguous_class_candidate_does_not_overresolve() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
    outcome_diagnostics: dict[str, int] = {}
    resolved = resolve_typescript_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        class_name_map={"Service": "repo.pkg.a.Service"},
        class_name_candidates={"Service": {"repo.pkg.a.Service", "repo.pkg.b.Service"}},
        instance_map={},
        class_instance_map={},
        outcome_diagnostics=outcome_diagnostics,
    )
    assert resolved == []
    assert outcome_diagnostics.get("ambiguous_candidate") == 1


def test_javascript_ambiguous_class_candidate_does_not_overresolve() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
    outcome_diagnostics: dict[str, int] = {}
    resolved = resolve_javascript_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        class_name_map={"Service": "repo.pkg.a.Service"},
        class_name_candidates={"Service": {"repo.pkg.a.Service", "repo.pkg.b.Service"}},
        instance_map={},
        class_instance_map={},
        outcome_diagnostics=outcome_diagnostics,
    )
    assert resolved == []
    assert outcome_diagnostics.get("ambiguous_candidate") == 1


def test_java_ambiguous_class_candidate_does_not_overresolve() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.Service": {"run"}},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={},
        class_name_map={"Service": "repo.pkg.a.Service"},
        class_name_candidates={"Service": {"repo.pkg.a.Service", "repo.pkg.b.Service"}},
        import_aliases={},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=lambda *_args: None,
    )
    assert resolved == []


def test_python_resolves_using_ir_qualified_call_when_text_is_unqualified() -> None:
    targets = [
        CallTarget(
            terminal="run",
            callee_text="run",
            ir=QualifiedCallIR(parts=("svc_alias", "run"), terminal="run"),
        )
    ]
    resolved = resolve_python_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        raw_module_map={},
        instance_map={},
        class_name_candidates={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="svc_alias",
                target="repo.pkg.services.Service",
                binding_kind="module_alias",
                evidence_kind="syntax_local_alias",
                language="python",
            ),
        ),
    )
    assert resolved == ["repo.pkg.services.Service.run"]


def test_python_resolves_using_ir_receiver_chain_when_text_is_unqualified() -> None:
    targets = [
        CallTarget(
            terminal="run",
            callee_text="run",
            receiver_chain=("self", "svc"),
            ir=ReceiverCallIR(receiver_chain=("self", "svc"), terminal="run"),
        )
    ]
    resolved = resolve_python_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.mod.Controller": {"run"}},
        class_name="repo.pkg.mod.Controller",
        raw_module_map={},
        instance_map={"svc": "repo.pkg.mod.Service"},
        class_name_candidates={},
    )
    assert resolved == ["repo.pkg.mod.Service.run"]


def test_typescript_resolves_using_ir_qualified_call_when_text_is_unqualified() -> None:
    targets = [
        CallTarget(
            terminal="run",
            callee_text="run",
            ir=QualifiedCallIR(parts=("svc_alias", "run"), terminal="run"),
        )
    ]
    resolved = resolve_typescript_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        class_name_map={},
        class_name_candidates={},
        instance_map={},
        class_instance_map={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="svc_alias",
                target="repo.pkg.services.Service",
                binding_kind="module_alias",
                evidence_kind="syntax_local_alias",
                language="typescript",
            ),
        ),
    )
    assert resolved == ["repo.pkg.services.Service.run"]


def test_typescript_resolves_imported_uppercase_receiver_call() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
    resolved = resolve_typescript_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        class_name_map={},
        class_name_candidates={},
        instance_map={},
        class_instance_map={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="Service",
                target="repo.pkg.services.Service",
                binding_kind="module_alias",
                evidence_kind="syntax_local_import",
                language="typescript",
            ),
        ),
    )
    assert resolved == ["repo.pkg.services.Service.run"]


def test_javascript_resolves_using_ir_qualified_call_when_text_is_unqualified() -> None:
    targets = [
        CallTarget(
            terminal="run",
            callee_text="run",
            ir=QualifiedCallIR(parts=("svc_alias", "run"), terminal="run"),
        )
    ]
    resolved = resolve_javascript_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        class_name_map={},
        class_name_candidates={},
        instance_map={},
        class_instance_map={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="svc_alias",
                target="repo.pkg.services.Service",
                binding_kind="module_alias",
                evidence_kind="syntax_local_alias",
                language="javascript",
            ),
        ),
    )
    assert resolved == ["repo.pkg.services.Service.run"]


def test_javascript_resolves_imported_uppercase_receiver_call() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
    resolved = resolve_javascript_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        class_name_map={},
        class_name_candidates={},
        instance_map={},
        class_instance_map={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="Service",
                target="repo.pkg.services.Service",
                binding_kind="module_alias",
                evidence_kind="syntax_local_import",
                language="javascript",
            ),
        ),
    )
    assert resolved == ["repo.pkg.services.Service.run"]


def test_javascript_prefers_imported_uppercase_receiver_over_ambiguous_local_candidates() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
    outcome_diagnostics: dict[str, int] = {}
    resolved = resolve_javascript_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        class_name_map={"Service": "repo.pkg.local.Service"},
        class_name_candidates={
            "Service": {"repo.pkg.local.Service", "repo.pkg.alt.Service"}
        },
        instance_map={},
        class_instance_map={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="Service",
                target="repo.pkg.services.Service",
                binding_kind="module_alias",
                evidence_kind="syntax_local_import",
                language="javascript",
            ),
        ),
        outcome_diagnostics=outcome_diagnostics,
    )
    assert resolved == ["repo.pkg.services.Service.run"]
    assert outcome_diagnostics.get("ambiguous_candidate") is None


def test_java_resolves_using_ir_qualified_call_when_text_is_unqualified() -> None:
    targets = [
        CallTarget(
            terminal="run",
            callee_text="run",
            ir=QualifiedCallIR(parts=("Service", "run"), terminal="run"),
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.Service": {"run"}},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={},
        class_name_map={"Service": "repo.pkg.Service"},
        class_name_candidates={"Service": {"repo.pkg.Service"}},
        import_aliases={"Service": "repo.pkg.Service"},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=lambda *_args: None,
        local_binding_facts=(
            LocalBindingFact(
                symbol="Service",
                target="repo.pkg.Service",
                binding_kind="constructor_or_classifier_import",
                evidence_kind="syntax_local_import",
                language="java",
            ),
        ),
    )
    assert resolved == ["repo.pkg.Service.run"]


def test_java_resolves_unqualified_calls_from_static_member_aliases() -> None:
    targets = [CallTarget(terminal="run", callee_text="run")]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.Service": {"run"}},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={},
        import_aliases={},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=lambda *_args: None,
        local_binding_facts=(
            LocalBindingFact(
                symbol="run",
                target="repo.pkg.Service.run",
                binding_kind="static_import_member",
                evidence_kind="syntax_local_import",
                language="java",
            ),
        ),
    )
    assert resolved == ["repo.pkg.Service.run"]


def test_python_member_alias_does_not_apply_to_receiver_calls() -> None:
    targets = [CallTarget(terminal="run", callee_text="svc.run")]
    resolved = resolve_python_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        raw_module_map={},
        instance_map={},
        class_name_candidates={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="run",
                target="repo.pkg.Service.run",
                binding_kind="direct_import_symbol",
                evidence_kind="syntax_local_import",
                language="python",
            ),
        ),
    )
    assert resolved == []


def test_python_module_fallback_respects_local_binding_shadowing() -> None:
    targets = [CallTarget(terminal="helper", callee_text="helper")]
    resolved = resolve_python_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions={"helper"},
        class_methods={},
        class_name=None,
        raw_module_map={},
        instance_map={},
        class_name_candidates={},
        local_binding_names={"helper"},
    )
    assert resolved == []


def test_typescript_member_alias_does_not_apply_to_receiver_calls() -> None:
    targets = [CallTarget(terminal="run", callee_text="svc.run")]
    resolved = resolve_typescript_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        class_name_map={},
        class_name_candidates={},
        instance_map={},
        class_instance_map={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="run",
                target="repo.pkg.Service.run",
                binding_kind="destructured_static_member",
                evidence_kind="syntax_local_destructuring",
                language="typescript",
            ),
        ),
    )
    assert resolved == []


def test_javascript_member_alias_does_not_apply_to_receiver_calls() -> None:
    targets = [CallTarget(terminal="run", callee_text="svc.run")]
    resolved = resolve_javascript_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name=None,
        class_name_map={},
        class_name_candidates={},
        instance_map={},
        class_instance_map={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="run",
                target="repo.pkg.Service.run",
                binding_kind="destructured_static_member",
                evidence_kind="syntax_local_destructuring",
                language="javascript",
            ),
        ),
    )
    assert resolved == []


def test_java_resolves_unqualified_calls_from_single_static_wildcard() -> None:
    targets = [CallTarget(terminal="run", callee_text="run")]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.Service": {"run"}},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={},
        import_aliases={},
        static_wildcard_targets={"repo.pkg.Service"},
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=lambda *_args: None,
    )
    assert resolved == ["repo.pkg.Service.run"]


def test_java_resolves_unqualified_calls_from_single_static_wildcard_without_local_methods() -> None:
    targets = [CallTarget(terminal="run", callee_text="run")]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={},
        import_aliases={},
        static_wildcard_targets={"repo.pkg.Service"},
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=lambda *_args: None,
    )
    assert resolved == ["repo.pkg.Service.run"]


def test_java_resolves_receiver_call_from_typed_parameter() -> None:
    targets = [
        CallTarget(
            terminal="run",
            callee_text="svc.run",
            ir=QualifiedCallIR(parts=("svc", "run"), terminal="run"),
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.Service": {"run"}},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={"Service": {"repo.pkg.Service"}},
        import_aliases={"Service": "repo.pkg.Service"},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={"svc": "Service"},
        module_prefix=None,
        qualify_java_type=qualify_java_type,
    )
    assert resolved == ["repo.pkg.Service.run"]


def test_java_resolves_unique_overload_by_argument_count() -> None:
    targets = [
        CallTarget(
            terminal="append",
            callee_text="builder.append",
            ir=QualifiedCallIR(parts=("builder", "append"), terminal="append"),
            argument_count=1,
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.Builder": {"append"}},
        class_method_overloads={
            "repo.pkg.Builder": {
                "append": {
                    1: {"repo.pkg.Builder.append-2"},
                    2: {"repo.pkg.Builder.append"},
                }
            }
        },
        class_ancestors={},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={"Builder": {"repo.pkg.Builder"}},
        import_aliases={"Builder": "repo.pkg.Builder"},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={"builder": "Builder"},
        module_prefix=None,
        qualify_java_type=qualify_java_type,
    )
    assert resolved == ["repo.pkg.Builder.append-2"]


def test_java_resolves_unqualified_call_from_nearest_ancestor() -> None:
    targets = [CallTarget(terminal="build", callee_text="build")]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={
            "repo.pkg.BaseBuilder": {"build"},
            "repo.pkg.Builder": set(),
        },
        class_method_overloads={},
        class_ancestors={"repo.pkg.Builder": ("repo.pkg.BaseBuilder",)},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={},
        import_aliases={},
        static_wildcard_targets=set(),
        class_name="repo.pkg.Builder",
        instance_types={},
        module_prefix=None,
        qualify_java_type=qualify_java_type,
    )
    assert resolved == ["repo.pkg.BaseBuilder.build"]


def test_java_resolves_typed_receiver_to_nearest_ancestor_owner() -> None:
    targets = [
        CallTarget(
            terminal="getKey",
            callee_text="pair.getKey",
            ir=QualifiedCallIR(parts=("pair", "getKey"), terminal="getKey"),
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={
            "repo.pkg.PairImpl": set(),
            "repo.pkg.Map.Entry": {"getKey"},
        },
        class_method_overloads={},
        class_ancestors={"repo.pkg.PairImpl": ("repo.pkg.Map.Entry",)},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={"PairImpl": {"repo.pkg.PairImpl"}},
        import_aliases={"PairImpl": "repo.pkg.PairImpl"},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={"pair": "PairImpl"},
        module_prefix=None,
        qualify_java_type=qualify_java_type,
    )
    assert resolved == ["repo.pkg.Map.Entry.getKey"]


def test_java_resolves_ancestor_owner_by_argument_count() -> None:
    targets = [
        CallTarget(
            terminal="append",
            callee_text="builder.append",
            ir=QualifiedCallIR(parts=("builder", "append"), terminal="append"),
            argument_count=1,
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={
            "repo.pkg.Formattable": {"append"},
            "repo.pkg.Appendable": {"append"},
            "repo.pkg.Builder": set(),
        },
        class_method_overloads={
            "repo.pkg.Formattable": {"append": {2: {"repo.pkg.Formattable.append"}}},
            "repo.pkg.Appendable": {"append": {1: {"repo.pkg.Appendable.append"}}},
        },
        class_ancestors={
            "repo.pkg.Builder": ("repo.pkg.Formattable", "repo.pkg.Appendable"),
        },
        class_kind_map={},
        class_name_map={},
        class_name_candidates={"Builder": {"repo.pkg.Builder"}},
        import_aliases={"Builder": "repo.pkg.Builder"},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={"builder": "Builder"},
        module_prefix=None,
        qualify_java_type=qualify_java_type,
    )
    assert resolved == ["repo.pkg.Appendable.append"]


def test_java_resolves_enum_synthetic_values_from_known_owner() -> None:
    targets = [
        CallTarget(
            terminal="values",
            callee_text="CollectionFeature.values",
            ir=QualifiedCallIR(parts=("CollectionFeature", "values"), terminal="values"),
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.CollectionFeature": set()},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={"repo.pkg.CollectionFeature": "enum"},
        class_name_map={},
        class_name_candidates={"CollectionFeature": {"repo.pkg.CollectionFeature"}},
        import_aliases={"CollectionFeature": "repo.pkg.CollectionFeature"},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=qualify_java_type,
    )
    assert resolved == ["repo.pkg.CollectionFeature.values"]


def test_java_does_not_resolve_unknown_owner_fallback() -> None:
    targets = [
        CallTarget(
            terminal="getKey",
            callee_text="Map.Entry.getKey",
            ir=QualifiedCallIR(parts=("Map", "Entry", "getKey"), terminal="getKey"),
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={},
        import_aliases={},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=qualify_java_type,
    )
    assert resolved == []


def test_java_does_not_resolve_unknown_enum_synthetic_values() -> None:
    targets = [
        CallTarget(
            terminal="values",
            callee_text="CollectionFeature.values",
            ir=QualifiedCallIR(parts=("CollectionFeature", "values"), terminal="values"),
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={},
        import_aliases={},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=qualify_java_type,
    )
    assert resolved == []


def test_java_resolves_dotted_nested_receiver_type_path() -> None:
    targets = [
        CallTarget(
            terminal="tryAdvance",
            callee_text="Spliterator.OfPrimitive.tryAdvance",
            ir=QualifiedCallIR(
                parts=("Spliterator", "OfPrimitive", "tryAdvance"),
                terminal="tryAdvance",
            ),
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.Spliterator.OfPrimitive": {"tryAdvance"}},
        class_method_overloads={},
        class_ancestors={},
        class_kind_map={"repo.pkg.Spliterator.OfPrimitive": "interface"},
        class_name_map={},
        class_name_candidates={"OfPrimitive": {"repo.pkg.Spliterator.OfPrimitive"}},
        import_aliases={},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={},
        module_prefix="repo.pkg",
        qualify_java_type=qualify_java_type,
    )
    assert resolved == ["repo.pkg.Spliterator.OfPrimitive.tryAdvance"]


def test_java_resolves_static_wildcard_target_by_argument_count() -> None:
    targets = [
        CallTarget(
            terminal="of",
            callee_text="of",
            argument_count=1,
        )
    ]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={
            "repo.pkg.Streams": {"of"},
            "repo.pkg.IntStreams": {"of"},
        },
        class_method_overloads={
            "repo.pkg.Streams": {"of": {2: {"repo.pkg.Streams.of"}}},
            "repo.pkg.IntStreams": {"of": {1: {"repo.pkg.IntStreams.of"}}},
        },
        class_ancestors={},
        class_kind_map={},
        class_name_map={},
        class_name_candidates={},
        import_aliases={},
        static_wildcard_targets={"repo.pkg.Streams", "repo.pkg.IntStreams"},
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=qualify_java_type,
    )
    assert resolved == ["repo.pkg.IntStreams.of"]


def test_java_qualify_type_returns_none_for_unresolved_bare_name() -> None:
    resolved = qualify_java_type(
        "Service",
        module_name="repo.pkg.mod",
        class_name_candidates={},
        import_aliases={},
        module_prefix=None,
    )
    assert resolved is None


def test_java_qualify_type_rejects_unproven_dotted_types() -> None:
    resolved = qualify_java_type(
        "java.util.List",
        module_name="repo.pkg.mod",
        class_name_candidates={},
        import_aliases={},
        module_prefix=None,
    )
    assert resolved is None


def test_java_qualify_type_prefers_unique_nested_class_path() -> None:
    resolved = qualify_java_type(
        "Map.Entry",
        module_name="repo.pkg.mod",
        class_name_candidates={"Entry": {"repo.pkg.Map.Entry", "repo.pkg.Other.Entry"}},
        import_aliases={},
        module_prefix="repo.pkg",
        class_path_candidates={"Map.Entry": {"repo.pkg.Map.Entry"}},
    )
    assert resolved == "repo.pkg.Map.Entry"
