# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.diagnostics.pre_persist.classifier import (
    classify_no_in_repo_candidate,
)
from sciona.code_analysis.diagnostics.pre_persist import pipeline as diagnostic_pipeline
from sciona.code_analysis.diagnostics.pre_persist.report import (
    _merge_non_candidate_buckets,
    build_verbose_payload,
)
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


def test_classifier_marks_reachable_repo_prefix_as_unindexed() -> None:
    observation = DiagnosticMissObservation(
        language="unknown",
        file_path="pkg/main.txt",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.models.Secret",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg", "repo.pkg.models"),
        reachable_repo_prefix_matches=("repo.pkg.models",),
        longest_reachable_repo_prefix_match="repo.pkg.models",
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_unindexed_symbol"
    assert classified.reasons == ("reachable_repo_owned_prefix",)


def test_classifier_marks_shallow_non_reachable_repo_prefix_as_external() -> None:
    observation = DiagnosticMissObservation(
        language="unknown",
        file_path="pkg/main.txt",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.Secret",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo",),
        longest_repo_prefix_match="repo",
        repo_prefix_match_depth=1,
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_external_dependency"
    assert classified.reasons == ("shallow_non_reachable_repo_prefix",)


def test_classifier_uses_repo_hint_overlap_for_unindexed() -> None:
    observation = DiagnosticMissObservation(
        language="unknown",
        file_path="pkg/main.txt",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="third.party.Secret",
        ordinal=1,
        callee_kind="qualified",
        candidate_module_hints=("repo.pkg.models", "third.party"),
        repo_hint_overlap=("repo.pkg.models",),
        identifier_root="third",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_unindexed_symbol"
    assert classified.reasons == ("repo_hint_overlap",)


def test_classifier_marks_external_module_hints_as_external() -> None:
    observation = DiagnosticMissObservation(
        language="unknown",
        file_path="pkg/main.txt",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="third.party.Secret",
        ordinal=1,
        callee_kind="qualified",
        candidate_module_hints=("third.party",),
        identifier_root="third",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_external_dependency"
    assert classified.reasons == ("qualified_identifier_with_external_module_hints",)


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
    assert classified.reasons == ("repo_owned_dynamic_member_terminal",)


def test_classifier_keeps_unknown_receiver_member_terminal_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="typescript",
        file_path="pkg/main.ts",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="value.map",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=(),
        identifier_root="value",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_dynamic_dispatch_or_indirect"
    assert classified.reasons == ("dynamic_member_terminal",)


def test_classifier_marks_extended_repo_owned_member_terminal_as_unindexed() -> None:
    observation = DiagnosticMissObservation(
        language="typescript",
        file_path="pkg/main.ts",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.provider.Provider.push",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg", "repo.pkg.provider"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_unindexed_symbol"
    assert classified.reasons == ("repo_owned_member_terminal",)


def test_classifier_marks_repo_owned_typescript_fluent_method_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="typescript",
        file_path="pkg/main.ts",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.provider.Provider.map",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg", "repo.pkg.provider"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_dynamic_dispatch_or_indirect"
    assert classified.reasons == ("repo_owned_dynamic_member_terminal",)


def test_classifier_keeps_repo_owned_typescript_exception_factory_as_unindexed() -> None:
    observation = DiagnosticMissObservation(
        language="typescript",
        file_path="pkg/main.ts",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.provider.Provider.exceptionFactory",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg", "repo.pkg.provider"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_unindexed_symbol"
    assert classified.reasons == ("repo_owned_member_terminal",)


def test_classifier_keeps_repo_owned_python_class_member_terminal_as_unindexed() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.models.Item.model_validate",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg", "repo.pkg.models"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_unindexed_symbol"
    assert classified.reasons == ("repo_owned_member_terminal",)


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


def test_classifier_marks_constructor_duplication_as_parser_gap() -> None:
    observation = DiagnosticMissObservation(
        language="java",
        file_path="pkg/Main.java",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.Main.run",
        caller_module="repo.pkg.Main",
        identifier="repo.pkg.Outer.Inner.Inner",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg", "repo.pkg.Outer"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_parser_extraction_gap"


def test_classifier_marks_namespace_chain_duplication_as_parser_gap() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.logger.logger.warning",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_parser_extraction_gap"


def test_classifier_marks_repeated_tail_pair_as_parser_gap() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.logger.warning.logger.warning",
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


def test_classifier_uses_javascript_global_root_refinement() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="pkg/main.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="Math.max",
        ordinal=1,
        callee_kind="qualified",
        identifier_root="Math",
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


def test_classifier_uses_python_stdlib_root_refinement() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="json.dumps",
        ordinal=1,
        callee_kind="qualified",
        identifier_root="json",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_standard_library_or_builtin"


def test_classifier_does_not_treat_repo_owned_python_stdlib_root_as_builtin() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="json.dumps",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("json",),
        longest_repo_prefix_match="json",
        repo_prefix_match_depth=1,
        identifier_root="json",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_external_dependency"
    assert classified.reasons == ("shallow_non_reachable_repo_prefix",)


def test_classifier_does_not_treat_repo_owned_javascript_global_as_builtin() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="pkg/main.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="Promise.resolve",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("Promise",),
        longest_repo_prefix_match="Promise",
        repo_prefix_match_depth=1,
        identifier_root="Promise",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_external_dependency"
    assert classified.reasons == ("shallow_non_reachable_repo_prefix",)


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


def test_diagnostic_observation_carries_repo_prefix_strength(monkeypatch) -> None:
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
            {"repo.pkg.mod": {"repo.pkg.models"}},
            {"repo.pkg.mod": {"repo.pkg.models"}},
            {"repo.pkg.mod": {"repo", "repo.pkg"}},
            {
                "repo.pkg": "pkg/__init__.py",
                "repo.pkg.mod": "pkg/mod.py",
                "repo.pkg.models": "pkg/models.py",
            },
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
        lambda **kwargs: {"repo.pkg.models": {"Secret"}},
    )
    monkeypatch.setattr(
        diagnostic_pipeline,
        "build_typescript_barrel_export_map",
        lambda **kwargs: {},
    )

    def _resolve(*args, pre_persist_observations, **kwargs):
        pre_persist_observations.append(
            PrePersistObservation(
                identifier="repo.pkg.models.Secret",
                ordinal=1,
                callee_kind="qualified",
                candidate_module_hints=("repo.pkg.models", "third.party"),
            )
        )
        return []

    monkeypatch.setattr(diagnostic_pipeline, "resolve_callees", _resolve)

    payload = diagnostic_pipeline.classify_pre_persist_misses(
        core_conn=None,
        snapshot_id="snap",
        call_records=[
            CallExtractionRecord(
                caller_structural_id="caller",
                caller_qualified_name="repo.pkg.mod.run",
                caller_node_type="callable",
                callee_identifiers=["repo.pkg.models.Secret"],
            )
        ],
    )

    observation = payload["observations"][0]
    assert observation["repo_prefix_matches"] == ["repo", "repo.pkg", "repo.pkg.models"]
    assert observation["longest_repo_prefix_match"] == "repo.pkg.models"
    assert observation["repo_prefix_match_depth"] == 3
    assert "deep_repo_prefix" in observation["signals"]
    assert "repo_prefix_depth:3" in observation["signals"]
    assert observation["reachable_repo_prefix_matches"] == [
        "repo",
        "repo.pkg",
        "repo.pkg.models",
    ]
    assert observation["longest_reachable_repo_prefix_match"] == "repo.pkg.models"
    assert observation["reachable_repo_binding"] is True
    assert observation["repo_hint_overlap"] == ["repo.pkg.models"]
    assert "reachable_repo_prefix" in observation["signals"]
    assert "reachable_repo_binding" in observation["signals"]
    assert "reachable_repo_prefix_depth:3" in observation["signals"]
    assert "repo_hint_overlap" in observation["signals"]
    assert "repo_hint_overlap_count:1" in observation["signals"]
    assert "candidate_module_hint" in observation["signals"]
    assert "candidate_hint_count:2" in observation["signals"]
    assert "identifier_depth:4" in observation["signals"]
    assert "owner_segment:value_like" in observation["signals"]


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
                    "signals": [
                        "candidate_hint_count:2",
                        "candidate_module_hint",
                        "deep_repo_prefix",
                        "identifier_depth:4",
                        "owner_segment:value_like",
                        "qualified_identifier",
                        "repo_hint_overlap",
                        "repo_hint_overlap_count:1",
                        "reachable_repo_binding",
                        "reachable_repo_prefix",
                        "reachable_repo_prefix_depth:3",
                        "repo_owned_prefix",
                        "repo_prefix_depth:3",
                    ],
                    "language": "python",
                    "file_path": "pkg/mod.py",
                    "caller_structural_id": "caller",
                    "caller_qualified_name": "repo.pkg.mod.run",
                    "caller_module": "repo.pkg.mod",
                    "identifier": "repo.pkg.models.Secret",
                    "identifier_root": "repo",
                    "ordinal": 1,
                    "callee_kind": "qualified",
                    "candidate_module_hints": ["repo.pkg.models", "third.party"],
                    "repo_prefix_matches": ["repo", "repo.pkg", "repo.pkg.models"],
                    "longest_repo_prefix_match": "repo.pkg.models",
                    "repo_prefix_match_depth": 3,
                    "reachable_repo_prefix_matches": [
                        "repo",
                        "repo.pkg",
                        "repo.pkg.models",
                    ],
                    "longest_reachable_repo_prefix_match": "repo.pkg.models",
                    "reachable_repo_binding": True,
                    "repo_hint_overlap": ["repo.pkg.models"],
                    "scope": "non_tests",
                }
            ]
        }
    )

    bucket_payload = payload["buckets"]["likely_unindexed_symbol"]
    assert bucket_payload["reasons"] == {"repo_owned_qualified_prefix": 1}
    assert bucket_payload["signals"] == {
        "candidate_hint_count:2": 1,
        "candidate_module_hint": 1,
        "deep_repo_prefix": 1,
        "identifier_depth:4": 1,
        "owner_segment:value_like": 1,
        "qualified_identifier": 1,
        "repo_hint_overlap": 1,
        "repo_hint_overlap_count:1": 1,
        "reachable_repo_binding": 1,
        "reachable_repo_prefix": 1,
        "reachable_repo_prefix_depth:3": 1,
        "repo_owned_prefix": 1,
        "repo_prefix_depth:3": 1,
    }
    assert bucket_payload["callsites"][0]["identifier_root"] == "repo"
    assert bucket_payload["callsites"][0]["repo_prefix_matches"] == [
        "repo",
        "repo.pkg",
        "repo.pkg.models",
    ]
    assert payload["problematic_files"][0]["reasons"] == {
        "repo_owned_qualified_prefix": 1
    }
    assert payload["problematic_files"][0]["signals"] == {
        "candidate_hint_count:2": 1,
        "candidate_module_hint": 1,
        "deep_repo_prefix": 1,
        "identifier_depth:4": 1,
        "owner_segment:value_like": 1,
        "qualified_identifier": 1,
        "repo_hint_overlap": 1,
        "repo_hint_overlap_count:1": 1,
        "reachable_repo_binding": 1,
        "reachable_repo_prefix": 1,
        "reachable_repo_prefix_depth:3": 1,
        "repo_owned_prefix": 1,
        "repo_prefix_depth:3": 1,
    }


def test_merge_non_candidate_buckets_preserves_canonical_keys() -> None:
    merged = _merge_non_candidate_buckets(
        {
            "accepted_outside_in_repo": 2,
            "invalid_observation_shape": 3,
        },
        {
            "accepted_outside_in_repo": 99,
            "invalid_observation_shape": 88,
            "likely_unindexed_symbol": 7,
        },
    )

    assert merged["accepted_outside_in_repo"] == 2
    assert merged["invalid_observation_shape"] == 3
    assert merged["likely_unindexed_symbol"] == 7
