# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.writes import write_index as artifact_write
from sciona.code_analysis.diagnostics.rejected_calls.classifier import (
    classify_no_in_repo_candidate,
    classify_positive_candidate_rejection,
)
from sciona.code_analysis.diagnostics.rejected_calls import pipeline as diagnostic_pipeline
from sciona.code_analysis.diagnostics.rejected_calls.report import (
    build_rejected_calls_verbose_payload,
    _merge_non_candidate_buckets,
    build_verbose_payload,
)
from sciona.code_analysis.diagnostics.rejected_calls.models import (
    DiagnosticMissObservation,
)
from sciona.code_analysis.core.extract.calls import CallExtractionRecord, RejectedObservation
from sciona.runtime import paths as runtime_paths
from sciona.runtime.paths import get_artifact_db_path
from tests.helpers import seed_repo_with_snapshot


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

    assert classified.bucket == "builtin_or_standard_shape"


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

    assert classified.bucket == "dynamic_or_indirect_shape"


def test_classifier_marks_fixture_or_generated_paths_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="unknown",
        file_path="test/form/samples/foo/_expected/module.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.fixture.helper",
        ordinal=1,
        callee_kind="qualified",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "dynamic_or_indirect_shape"
    assert classified.reasons == ("fixture_or_generated_path",)


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

    assert classified.bucket == "unindexed_symbol_shape"


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

    assert classified.bucket == "unindexed_symbol_shape"
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

    assert classified.bucket == "external_dependency_shape"
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

    assert classified.bucket == "unindexed_symbol_shape"
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

    assert classified.bucket == "external_dependency_shape"
    assert classified.reasons == ("qualified_identifier_with_external_module_hints",)


def test_classifier_uses_local_binding_target_for_qualified_identifier() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="src/controllers/admin/dashboard.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.src.controllers.admin.dashboard.run",
        caller_module="repo.src.controllers.admin.dashboard",
        identifier="translator.translateKeys",
        ordinal=1,
        callee_kind="qualified",
        candidate_module_hints=("vendor.i18n",),
        identifier_root="translator",
        local_binding_symbol="translator",
        local_binding_target="repo.public.src.translator",
        local_binding_kind="module_alias",
        local_binding_evidence_kind="syntax_local_import",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "unindexed_symbol_shape"
    assert classified.reasons == ("binding_backed_module_alias",)


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

    assert classified.bucket == "dynamic_or_indirect_shape"
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

    assert classified.bucket == "dynamic_or_indirect_shape"
    assert classified.reasons == ("dynamic_member_terminal",)


def test_classifier_marks_typescript_finally_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="typescript",
        file_path="pkg/main.ts",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.promise.finally",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "dynamic_or_indirect_shape"
    assert classified.reasons == ("repo_owned_dynamic_member_terminal",)


def test_classifier_marks_javascript_has_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="pkg/main.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.cache.has",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "dynamic_or_indirect_shape"
    assert classified.reasons == ("repo_owned_dynamic_member_terminal",)


def test_classifier_marks_common_finally_terminal_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="unknown",
        file_path="pkg/main.txt",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="promise.finally",
        ordinal=1,
        callee_kind="qualified",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "dynamic_or_indirect_shape"
    assert classified.reasons == ("fluent_terminal",)


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

    assert classified.bucket == "unindexed_symbol_shape"
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

    assert classified.bucket == "dynamic_or_indirect_shape"
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

    assert classified.bucket == "unindexed_symbol_shape"
    assert classified.reasons == ("repo_owned_member_terminal",)


def test_classifier_marks_report_style_vscode_reduce_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="typescript",
        file_path="pkg/main.ts",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.range.Range.reduce",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg", "repo.pkg.range"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "dynamic_or_indirect_shape"
    assert classified.reasons == ("repo_owned_dynamic_member_terminal",)


def test_classifier_marks_report_style_fastapi_model_validate_as_unindexed() -> None:
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

    assert classified.bucket == "unindexed_symbol_shape"
    assert classified.reasons == ("repo_owned_member_terminal",)


def test_classifier_marks_report_style_airbyte_parse_obj_as_unindexed() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.models.AirbyteCatalog.parse_obj",
        ordinal=1,
        callee_kind="qualified",
        repo_prefix_matches=("repo", "repo.pkg", "repo.pkg.models"),
        identifier_root="repo",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "unindexed_symbol_shape"
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

    assert classified.bucket == "unindexed_symbol_shape"
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

    assert classified.bucket == "parser_extraction_mismatch"


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

    assert classified.bucket == "parser_extraction_mismatch"


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

    assert classified.bucket == "parser_extraction_mismatch"


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

    assert classified.bucket == "parser_extraction_mismatch"


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

    assert classified.bucket == "builtin_or_standard_shape"


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

    assert classified.bucket == "builtin_or_standard_shape"


def test_positive_candidate_classifier_uses_raw_drop_reason() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="pkg/main.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.api.run",
        ordinal=1,
        callee_kind="qualified",
        gate_reason="insufficient_static_evidence",
        raw_drop_reason="unique_without_provenance",
    )

    classified = classify_positive_candidate_rejection(observation)

    assert classified.bucket == "unindexed_symbol_shape"
    assert classified.reasons == ("positive_candidate_without_provenance",)


def test_positive_candidate_classifier_marks_invalid_shape_as_parser_gap() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.pkg.api.run",
        ordinal=1,
        callee_kind="qualified",
        gate_reason="insufficient_static_evidence",
        raw_drop_reason="invalid_observation_shape",
    )

    classified = classify_positive_candidate_rejection(observation)

    assert classified.bucket == "parser_extraction_mismatch"
    assert classified.reasons == ("positive_candidate_invalid_shape",)


def test_positive_candidate_classifier_marks_index_proxy_surface_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="src/api/users.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="repo.database.index.sortedSetAdd",
        ordinal=1,
        callee_kind="qualified",
        gate_reason="insufficient_static_evidence",
        raw_drop_reason="unique_without_provenance",
    )

    classified = classify_positive_candidate_rejection(observation)

    assert classified.bucket == "dynamic_or_indirect_shape"
    assert classified.reasons == ("runtime_composed_index_surface",)


def test_positive_candidate_classifier_marks_fixture_scope_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="test/form/samples/foo/_expected/module.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="parser.enterRule",
        ordinal=1,
        callee_kind="qualified",
        gate_reason="insufficient_static_evidence",
        raw_drop_reason="unique_without_provenance",
    )

    classified = classify_positive_candidate_rejection(observation)

    assert classified.bucket == "dynamic_or_indirect_shape"
    assert classified.reasons == ("fixture_or_generated_path",)


def test_positive_candidate_classifier_uses_local_binding_target_for_no_candidates() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="src/controllers/admin/dashboard.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.src.controllers.admin.dashboard.run",
        caller_module="repo.src.controllers.admin.dashboard",
        identifier="translator.translateKeys",
        ordinal=1,
        callee_kind="qualified",
        local_binding_symbol="translator",
        local_binding_target="repo.public.src.translator",
        local_binding_kind="module_alias",
        local_binding_evidence_kind="syntax_local_import",
        gate_reason="insufficient_static_evidence",
        raw_drop_reason="no_candidates",
    )

    classified = classify_positive_candidate_rejection(observation)

    assert classified.bucket == "unindexed_symbol_shape"
    assert classified.reasons == ("binding_backed_module_alias_no_candidates",)


def test_positive_candidate_classifier_prefers_binding_backed_without_provenance() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="src/controllers/admin/dashboard.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.src.controllers.admin.dashboard.run",
        caller_module="repo.src.controllers.admin.dashboard",
        identifier="translator.translateKeys",
        ordinal=1,
        callee_kind="qualified",
        local_binding_symbol="translator",
        local_binding_target="repo.public.src.translator",
        local_binding_kind="module_alias",
        local_binding_evidence_kind="syntax_local_import",
        gate_reason="insufficient_static_evidence",
        raw_drop_reason="unique_without_provenance",
    )

    classified = classify_positive_candidate_rejection(observation)

    assert classified.bucket == "unindexed_symbol_shape"
    assert classified.reasons == ("binding_backed_module_alias_without_provenance",)


def test_positive_candidate_classifier_marks_inline_dynamic_chain_as_dynamic() -> None:
    observation = DiagnosticMissObservation(
        language="javascript",
        file_path="src/socket.js",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="socket.in(room).emit",
        ordinal=1,
        callee_kind="qualified",
        gate_reason="insufficient_static_evidence",
        raw_drop_reason="ambiguous_multiple_in_scope_candidates",
    )

    classified = classify_positive_candidate_rejection(observation)

    assert classified.bucket == "dynamic_or_indirect_shape"
    assert classified.reasons == ("inline_dynamic_call_chain",)


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

    assert classified.bucket == "builtin_or_standard_shape"


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

    assert classified.bucket == "builtin_or_standard_shape"


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

    assert classified.bucket == "external_dependency_shape"
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

    assert classified.bucket == "external_dependency_shape"
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

    assert classified.bucket == "external_dependency_shape"


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

    def _resolve(*args, rejected_observations, **kwargs):
        rejected_observations.append(
            RejectedObservation(
                identifier="repo.pkg.models.Secret",
                ordinal=1,
                callee_kind="qualified",
                candidate_module_hints=("repo.pkg.models", "third.party"),
            )
        )
        return []

    monkeypatch.setattr(diagnostic_pipeline, "resolve_callees", _resolve)

    payload = diagnostic_pipeline.classify_rejected_observations(
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


def test_classify_rejected_observations_uses_progress_factory(monkeypatch) -> None:
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

    def _resolve(*args, rejected_observations, **kwargs):
        rejected_observations.append(
            RejectedObservation(
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

    payload = diagnostic_pipeline.classify_rejected_observations(
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

    assert payload["totals"]["unindexed_symbol_shape"] == 1
    assert len(payload["observations"]) == 1
    assert events == [
        ("factory", ("Diagnostic classification", 1)),
        ("advance", 1),
        ("close", None),
    ]


def test_classify_rejected_calls_uses_temp_rejected_rows(tmp_path) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_write.reset_temp_rejected_callsites(artifact_conn)
        artifact_write.store_temp_rejected_callsites(
            artifact_conn,
            caller_structural_id="meth_alpha",
            caller_qualified_name=f"{prefix}.pkg.alpha.Service.run",
            caller_module=f"{prefix}.pkg.alpha",
            caller_language="python",
            caller_file_path="pkg/alpha/service.py",
            rows=[
                (
                    (
                        f"{prefix}.pkg.models.Secret",
                        "dropped",
                        None,
                        None,
                        "no_candidates",
                        0,
                        "qualified",
                        None,
                        None,
                        1,
                        0,
                        f"{prefix}.pkg.models",
                    ),
                    "no_in_repo_candidate",
                    "no_candidates",
                ),
                (
                    (
                        "external.helper",
                        "accepted",
                        "external_callable",
                        "exact_qname",
                        None,
                        1,
                        "qualified",
                        None,
                        None,
                        2,
                        1,
                        "external",
                    ),
                    "outside_in_repo_scope",
                    None,
                ),
            ],
        )

        events: list[tuple[str, object]] = []

        class _Handle:
            def advance(self, steps: int = 1) -> None:
                events.append(("advance", steps))

            def close(self) -> None:
                events.append(("close", None))

        def _factory(label: str, total: int):
            events.append(("factory", (label, total)))
            return _Handle()

        payload = diagnostic_pipeline.classify_rejected_calls(
            core_conn=core_conn,
            artifact_conn=artifact_conn,
            snapshot_id=snapshot_id,
            progress_factory=_factory,
        )
    finally:
        artifact_conn.close()
        core_conn.close()

    assert payload["totals"]["unindexed_symbol_shape"] == 1
    assert payload["totals"]["outside_in_repo_scope"] == 1
    assert events == [
        ("factory", ("Diagnostic classification", 2)),
        ("advance", 1),
        ("advance", 1),
        ("close", None),
    ]
    observations = payload["observations"]
    assert observations[0]["gate_reason"] == "no_in_repo_candidate"
    assert observations[0]["raw_drop_reason"] == "no_candidates"
    assert observations[1]["gate_reason"] == "outside_in_repo_scope"


def test_build_verbose_payload_includes_reason_and_prefix_traces() -> None:
    payload = build_verbose_payload(
        {
            "observations": [
                {
                    "bucket": "unindexed_symbol_shape",
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

    bucket_payload = payload["buckets"]["unindexed_symbol_shape"]
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


def test_build_rejected_calls_verbose_payload_combines_both_phases() -> None:
    payload = build_rejected_calls_verbose_payload(
        {
            "observations": [
                {
                    "bucket": "unindexed_symbol_shape",
                    "reasons": ["repo_owned_qualified_prefix"],
                    "signals": ["qualified_identifier"],
                    "language": "python",
                    "file_path": "pkg/mod.py",
                    "identifier": "repo.pkg.models.Secret",
                }
            ]
        },
        {
            "persisted_drop_observations": [
                {
                    "file_path": "pkg/mod.py",
                    "identifier": "socket.in(room).emit",
                    "drop_reason": "ambiguous_multiple_in_scope_candidates",
                    "candidate_count": 2,
                }
            ]
        },
    )

    assert payload["buckets"]["insufficient_static_evidence"]["count"] == 1
    assert payload["buckets"]["outside_static_contract"]["count"] == 1
    assert payload["problematic_callsites"][0]["public_bucket"] == "insufficient_static_evidence"
    assert payload["problematic_callsites"][1]["public_bucket"] == "outside_static_contract"
    assert payload["problematic_files"][0]["file_path"] == "pkg/mod.py"


def test_build_rejected_calls_verbose_payload_infers_phase_from_gate_reason() -> None:
    payload = build_rejected_calls_verbose_payload(
        {
            "observations": [
                {
                    "bucket": "unindexed_symbol_shape",
                    "reasons": ["repo_owned_qualified_prefix"],
                    "signals": ["qualified_identifier"],
                    "language": "python",
                    "file_path": "pkg/mod.py",
                    "identifier": "repo.pkg.models.Secret",
                    "gate_reason": "no_in_repo_candidate",
                },
                {
                    "bucket": "dynamic_or_indirect_shape",
                    "reasons": ["promise_terminal"],
                    "signals": ["qualified_identifier"],
                    "language": "javascript",
                    "file_path": "pkg/mod.py",
                    "identifier": "socket.in(room).emit",
                    "gate_reason": "insufficient_static_evidence",
                    "raw_drop_reason": "ambiguous_multiple_in_scope_candidates",
                },
            ]
        },
        None,
    )



def test_build_rejected_calls_verbose_payload_marks_index_proxy_surface_outside_contract() -> None:
    payload = build_rejected_calls_verbose_payload(
        {"observations": []},
        {
            "persisted_drop_observations": [
                {
                    "file_path": "src/api/users.js",
                    "identifier": "repo.database.index.sortedSetAdd",
                    "drop_reason": "unique_without_provenance",
                    "candidate_count": 1,
                }
            ]
        },
    )

    assert payload["buckets"]["outside_static_contract"]["count"] == 1
    assert payload["problematic_callsites"][0]["public_bucket"] == "outside_static_contract"


def test_build_rejected_calls_verbose_payload_marks_fixture_scope_outside_contract() -> None:
    payload = build_rejected_calls_verbose_payload(
        {"observations": []},
        {
            "persisted_drop_observations": [
                {
                    "file_path": "test/form/samples/foo/_expected/module.js",
                    "identifier": "parser.enterRule",
                    "drop_reason": "unique_without_provenance",
                    "candidate_count": 1,
                }
            ]
        },
    )

    assert payload["buckets"]["outside_static_contract"]["count"] == 1
    assert payload["problematic_callsites"][0]["public_bucket"] == "outside_static_contract"


def test_merge_diagnostic_payloads_combines_both_rejection_populations() -> None:
    payload = diagnostic_pipeline.merge_diagnostic_payloads(
        {
            "totals": {
                "unindexed_symbol_shape": 1,
                "external_dependency_shape": 2,
            },
            "by_language": {
                "python": {
                    "unindexed_symbol_shape": 1,
                    "external_dependency_shape": 2,
                }
            },
            "by_scope": {
                "non_tests": {
                    "unindexed_symbol_shape": 1,
                    "external_dependency_shape": 2,
                },
                "tests": {},
            },
            "observations": [
                {
                    "bucket": "unindexed_symbol_shape",
                    "identifier": "repo.pkg.models.Secret",
                    "file_path": "pkg/mod.py",
                }
            ],
        },
        {
            "totals": {
                "dynamic_or_indirect_shape": 3,
            },
            "by_language": {
                "javascript": {
                    "dynamic_or_indirect_shape": 3,
                }
            },
            "by_scope": {
                "non_tests": {
                    "dynamic_or_indirect_shape": 1,
                },
                "tests": {
                    "dynamic_or_indirect_shape": 2,
                },
            },
            "observations": [
                {
                    "bucket": "dynamic_or_indirect_shape",
                    "identifier": "socket.in(room).emit",
                    "file_path": "pkg/mod.js",
                    "gate_reason": "insufficient_static_evidence",
                }
            ],
        },
    )

    assert payload["totals"] == {
        "external_dependency_shape": 2,
        "builtin_or_standard_shape": 0,
        "dynamic_or_indirect_shape": 3,
        "unindexed_symbol_shape": 1,
        "parser_extraction_mismatch": 0,
        "no_clear_in_repo_target": 0,
        "outside_in_repo_scope": 0,
        "invalid_observation_shape": 0,
    }
    assert payload["by_language"]["python"]["unindexed_symbol_shape"] == 1
    assert (
        payload["by_language"]["javascript"]["dynamic_or_indirect_shape"]
        == 3
    )
    assert (
        payload["by_scope"]["non_tests"]["dynamic_or_indirect_shape"] == 1
    )
    assert payload["by_scope"]["tests"]["dynamic_or_indirect_shape"] == 2
    assert len(payload["observations"]) == 2


def test_build_rejected_calls_verbose_payload_counts_merged_pre_and_post_persist() -> None:
    payload = build_rejected_calls_verbose_payload(
        diagnostic_pipeline.merge_diagnostic_payloads(
            {
                "totals": {"unindexed_symbol_shape": 1},
                "by_language": {},
                "by_scope": {"non_tests": {}, "tests": {}},
                "observations": [
                    {
                        "bucket": "unindexed_symbol_shape",
                        "reasons": ["repo_owned_qualified_prefix"],
                        "signals": ["qualified_identifier"],
                        "language": "python",
                        "file_path": "pkg/mod.py",
                        "identifier": "repo.pkg.models.Secret",
                    }
                ],
            },
            {
                "totals": {"dynamic_or_indirect_shape": 1},
                "by_language": {},
                "by_scope": {"non_tests": {}, "tests": {}},
                "observations": [
                    {
                        "bucket": "dynamic_or_indirect_shape",
                        "reasons": ["promise_terminal"],
                        "signals": ["qualified_identifier"],
                        "language": "javascript",
                        "file_path": "pkg/mod.js",
                        "identifier": "socket.in(room).emit",
                        "gate_reason": "insufficient_static_evidence",
                        "raw_drop_reason": "ambiguous_multiple_in_scope_candidates",
                    }
                ],
            },
        ),
        None,
    )



def test_merge_non_candidate_buckets_projects_public_buckets() -> None:
    merged = _merge_non_candidate_buckets(
        {
            "outside_in_repo_scope": 2,
            "invalid_observation_shape": 3,
        },
        {
            "outside_in_repo_scope": 99,
            "invalid_observation_shape": 88,
            "unindexed_symbol_shape": 7,
        },
    )

    assert merged == {
        "outside_static_contract": 101,
        "insufficient_static_evidence": 7,
        "structural_mismatch": 91,
        "unclassified": 0,
    }
