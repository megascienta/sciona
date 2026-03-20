# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.calls import normalize_call_identifiers


def test_normalize_call_identifiers_is_scoped_by_language_and_module() -> None:
    resolved = [
        (
            "python",
            "repo.pkg.alpha.task.run",
            "function",
            ["repo.pkg.alpha.services.Service.run"],
        ),
        (
            "python",
            "repo.pkg.beta.task.run",
            "function",
            ["repo.pkg.beta.handlers.Runner.run"],
        ),
        (
            "typescript",
            "repo.pkg.alpha.task.run",
            "function",
            ["repo.pkg.alpha.services.Service.run"],
        ),
    ]

    normalized = normalize_call_identifiers(resolved)
    by_caller = {
        (language, qualified): set(callees)
        for language, qualified, _node_type, callees in normalized
    }

    assert by_caller[("python", "repo.pkg.alpha.task.run")] == {
        "repo.pkg.alpha.services.Service.run"
    }
    assert by_caller[("typescript", "repo.pkg.alpha.task.run")] == {
        "repo.pkg.alpha.services.Service.run"
    }
    # Different python module keeps its own unambiguous mapping.
    assert by_caller[("python", "repo.pkg.beta.task.run")] == {
        "repo.pkg.beta.handlers.Runner.run"
    }


def test_normalize_call_identifiers_keeps_dotted_names_when_terminal_is_ambiguous() -> None:
    resolved = [
        (
            "python",
            "repo.pkg.alpha.task.run",
            "function",
            ["repo.pkg.alpha.A.foo", "repo.pkg.alpha.B.foo"],
        ),
        (
            "python",
            "repo.pkg.alpha.task.other",
            "function",
            ["repo.pkg.alpha.A.foo"],
        ),
    ]

    normalized = normalize_call_identifiers(resolved)
    by_caller = {
        (language, qualified): set(callees)
        for language, qualified, _node_type, callees in normalized
    }
    assert by_caller[("python", "repo.pkg.alpha.task.run")] == {
        "repo.pkg.alpha.A.foo",
        "repo.pkg.alpha.B.foo",
    }
    assert by_caller[("python", "repo.pkg.alpha.task.other")] == {
        "repo.pkg.alpha.A.foo"
    }


def test_normalize_call_identifiers_promotes_unique_bare_terminal_only() -> None:
    resolved = [
        (
            "python",
            "repo.pkg.alpha.task.run",
            "function",
            ["repo.pkg.alpha.services.Service.run"],
        ),
        (
            "python",
            "repo.pkg.alpha.task.use",
            "function",
            ["run", "other"],
        ),
    ]

    normalized = normalize_call_identifiers(resolved)
    by_caller = {
        (language, qualified): tuple(callees)
        for language, qualified, _node_type, callees in normalized
    }
    assert by_caller[("python", "repo.pkg.alpha.task.use")] == (
        "repo.pkg.alpha.services.Service.run",
        "other",
    )
