# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.languages.java_calls import resolve_java_calls
from sciona.code_analysis.core.extract.languages.python_calls import resolve_python_calls
from sciona.code_analysis.core.extract.languages.typescript_calls import (
    resolve_typescript_calls,
)
from sciona.code_analysis.tools.call_extraction import CallTarget


def test_python_ambiguous_class_candidate_does_not_overresolve() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
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
    )
    assert resolved == []


def test_typescript_ambiguous_class_candidate_does_not_overresolve() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
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
    )
    assert resolved == []


def test_java_ambiguous_class_candidate_does_not_overresolve() -> None:
    targets = [CallTarget(terminal="run", callee_text="Service.run")]
    resolved = resolve_java_calls(
        targets=targets,
        module_name="repo.pkg.mod",
        module_functions=set(),
        class_methods={},
        class_name_map={"Service": "repo.pkg.a.Service"},
        class_name_candidates={"Service": {"repo.pkg.a.Service", "repo.pkg.b.Service"}},
        import_class_map={},
        class_name=None,
        instance_types={},
        module_prefix=None,
        qualify_java_type=lambda *_args: None,
    )
    assert resolved == []
