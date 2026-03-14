# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.diagnostics.pre_persist.classifier import (
    classify_no_in_repo_candidate,
)
from sciona.code_analysis.diagnostics.pre_persist import pipeline as diagnostic_pipeline
from sciona.code_analysis.diagnostics.pre_persist.report import build_verbose_payload
from sciona.code_analysis.diagnostics.pre_persist.models import (
    DiagnosticMissObservation,
)
from sciona.code_analysis.tools.call_extraction import CallExtractionRecord, PrePersistObservation


def test_classifier_marks_common_builtin_name() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="print",
        ordinal=1,
        callee_kind="terminal",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_standard_library_or_builtin"


def test_classifier_marks_dynamic_receiver_pattern() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="self.helper",
        ordinal=1,
        callee_kind="qualified",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_dynamic_dispatch_or_indirect"


def test_classifier_marks_repo_owned_qualified_name_as_unindexed() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.models.Secret",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg", "repo.pkg.models"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_unindexed_symbol"


def test_classifier_marks_dynamic_member_terminal() -> None:
    observation = DiagnosticMissObservation(
        language="typescript",
        file_path="pkg/main.ts",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.array.push",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_dynamic_dispatch_or_indirect"


def test_classifier_marks_repeated_segments_as_parser_gap() -> None:
    observation = DiagnosticMissObservation(
        language="java",
        file_path="pkg/Main.java",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.Main.run",
        caller_module="repo.pkg.Main",
        identifier="repo.pkg.Main.Main.Main",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_parser_extraction_gap"


def test_classifier_uses_javascript_global_refinement() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="pkg/main.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="console.log",
        ordinal=1,
        callee_kind="qualified",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_standard_library_or_builtin"


def test_classifier_uses_java_stdlib_refinement() -> None:
    observation = DiagnosticMissObservation(
        language="java",
        file_path="pkg/Main.java",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.Main.run",
        caller_module="repo.pkg.Main",
        identifier="System.out.println",
        ordinal=1,
        callee_kind="qualified",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_standard_library_or_builtin"


def test_classifier_keeps_non_repo_qualified_name_as_external() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="requests.sessions.Session",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=(),
        identifier_root="requests",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_external_dependency"


def test_classify_pre_persist_misses_uses_progress_factory(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostic_pipeline,
        "build_symbol_index",
        lambda core_conn, snapshot_id: ({}, set(), {"caller": "repo.pkg.mod.run"}),
    )
    monkeypatch.setattr(
        diagnostic_pipeline,
        "build_module_context",
        lambda core_conn, snapshot_id: (
            {"caller": "repo.pkg.mod"},
            {},
            {},
            {},
            {"repo.pkg.mod": "pkg/mod.py"},
        ),
    )
    monkeypatch.setattr(
        diagnostic_pipeline.core_read,
        "caller_node_metadata_map",
        lambda core_conn, snapshot_id: {
            "caller": {"language": "python", "file_path": "pkg/mod.py"}
        },
    )
    monkeypatch.setattr(
        diagnostic_pipeline.core_read,
        "caller_language_map",
        lambda core_conn, snapshot_id: {"caller": "python"},
    )
    monkeypatch.setattr(
        diagnostic_pipeline,
        "build_module_binding_index",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        diagnostic_pipeline,
        "build_typescript_barrel_export_map",
        lambda **kwargs: {},
    )

    def _resolve(*args, pre_persist_observations, **kwargs):
        pre_persist_observations.append(
            PrePersistObservation(
                identifier="repo.pkg.symbol.Missing",
                ordinal=1,
                callee_kind="qualified",
                candidate_module_hints=(),
            )
        )
        return []

    monkeypatch.setattr(diagnostic_pipeline, "resolve_callees", _resolve)

    events: list[tuple[str, object]] = []

    class _Handle:
        def advance(self, steps: int = 1) -> None:
            events.append(("advance", steps))

        def close(self) -> None:
            events.append(("close", None))

    def _factory(label: str, total: int):
        events.append(("factory", (label, total)))
        return _Handle()

    payload = diagnostic_pipeline.classify_pre_persist_misses(
        core_conn=None,
        snapshot_id="snap",
        call_records=[
            CallExtractionRecord(
                caller_structural_id="caller",
                caller_qualified_name="repo.pkg.mod.run",
                caller_node_type="callable",
                callee_identifiers=["repo.pkg.symbol.Missing"],
            )
        ],
        progress_factory=_factory,
    )

    assert payload["totals"]["likely_unindexed_symbol"] == 1
    assert len(payload["observations"]) == 1
    assert events == [
        ("factory", ("Diagnostic classification", 1)),
        ("advance", 1),
        ("close", None),
    ]


def test_build_verbose_payload_includes_reason_and_prefix_traces() -> None:
    payload = build_verbose_payload(
        {
            "observations": [
                {
                    "bucket": "likely_unindexed_symbol",
                    "reasons": ["repo_owned_qualified_prefix"],
                    "language": "python",
                    "file_path": "pkg/mod.py",
                    "caller_structural_id": "caller",
                    "caller_qualified_name": "repo.pkg.mod.run",
                    "caller_module": "repo.pkg.mod",
                    "identifier": "repo.pkg.models.Secret",
                    "identifier_root": "repo",
                    "ordinal": 1,
                    "callee_kind": "qualified",
                    "candidate_module_hints": [],
                    "repo_prefix_matches": ["repo", "repo.pkg", "repo.pkg.models"],
                    "scope": "non_tests",
                }
            ]
        }
    )

    bucket_payload = payload["buckets"]["likely_unindexed_symbol"]
    assert bucket_payload["reasons"] == {"repo_owned_qualified_prefix": 1}
    assert bucket_payload["callsites"][0]["identifier_root"] == "repo"
    assert bucket_payload["callsites"][0]["repo_prefix_matches"] == [
        "repo",
        "repo.pkg",
        "repo.pkg.models",
    ]
    assert payload["problematic_files"][0]["reasons"] == {
        "repo_owned_qualified_prefix": 1
    }
