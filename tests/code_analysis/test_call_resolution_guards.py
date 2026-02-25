# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.languages.java_calls import resolve_java_calls
from sciona.code_analysis.core.extract.languages.python_calls import resolve_python_calls
from sciona.code_analysis.core.extract.languages.typescript_calls import (
    resolve_typescript_calls,
)
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
        import_aliases={},
        member_aliases={},
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
        import_aliases={},
        member_aliases={},
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
        class_methods={},
        class_name_map={"Service": "repo.pkg.a.Service"},
        class_name_candidates={"Service": {"repo.pkg.a.Service", "repo.pkg.b.Service"}},
        import_aliases={},
        member_aliases={},
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
        import_aliases={"svc_alias": "repo.pkg.services.Service"},
        member_aliases={},
        raw_module_map={},
        instance_map={},
        class_name_candidates={},
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
        import_aliases={},
        member_aliases={},
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
        import_aliases={"svc_alias": "repo.pkg.services.Service"},
        member_aliases={},
        class_name_map={},
        class_name_candidates={},
        instance_map={},
        class_instance_map={},
    )
    assert resolved == ["repo.pkg.services.Service.run"]


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
        class_methods={},
        class_name_map={"Service": "repo.pkg.Service"},
        class_name_candidates={"Service": {"repo.pkg.Service"}},
        import_aliases={"Service": "repo.pkg.Service"},
        member_aliases={},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=lambda *_args: None,
    )
    assert resolved == ["repo.pkg.Service.run"]


def test_java_resolves_unqualified_calls_from_static_member_aliases() -> None:
    targets = [CallTarget(terminal="run", callee_text="run")]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name_map={},
        class_name_candidates={},
        import_aliases={},
        member_aliases={"run": "repo.pkg.Service.run"},
        static_wildcard_targets=set(),
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=lambda *_args: None,
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
        import_aliases={},
        member_aliases={"run": "repo.pkg.Service.run"},
        raw_module_map={},
        instance_map={},
        class_name_candidates={},
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
        import_aliases={},
        member_aliases={"run": "repo.pkg.Service.run"},
        class_name_map={},
        class_name_candidates={},
        instance_map={},
        class_instance_map={},
    )
    assert resolved == []


def test_java_resolves_unqualified_calls_from_single_static_wildcard() -> None:
    targets = [CallTarget(terminal="run", callee_text="run")]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={"repo.pkg.Service": {"run"}},
        class_name_map={},
        class_name_candidates={},
        import_aliases={},
        member_aliases={},
        static_wildcard_targets={"repo.pkg.Service"},
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=lambda *_args: None,
    )
    assert resolved == ["repo.pkg.Service.run"]
