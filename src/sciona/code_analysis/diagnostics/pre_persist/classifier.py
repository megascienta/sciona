# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Best-effort classification for rejected-call observations."""

from __future__ import annotations

from .languages import java, javascript, python, typescript
from .languages.common import classify_common
from .models import DiagnosticClassification, DiagnosticMissObservation


def _is_fixture_or_generated_path(file_path: str) -> bool:
    parts = [
        segment.lower()
        for segment in file_path.replace("\\", "/").split("/")
        if segment
    ]
    markers = {
        "__fixtures__",
        "fixture",
        "fixtures",
        "_expected",
        "expected",
        "generated",
        "__generated__",
        "snapshots",
        "__snapshots__",
    }
    return any(part in markers for part in parts)


def _is_dynamic_terminal(identifier: str) -> bool:
    terminal = identifier.rsplit(".", 1)[-1].strip().lower()
    return terminal in {
        "then",
        "catch",
        "finally",
        "map",
        "filter",
        "reduce",
        "slice",
        "some",
        "has",
        "keys",
        "values",
        "entries",
        "includes",
        "push",
        "pop",
        "clear",
    }


def _is_inline_dynamic_chain(identifier: str) -> bool:
    return ".in(" in identifier or ("(" in identifier and ")." in identifier)


def classify_no_in_repo_candidate(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification:
    language = observation.language.strip().lower()
    if language == "python":
        classified = python.classify(observation)
    elif language == "javascript":
        classified = javascript.classify(observation)
    elif language == "typescript":
        classified = typescript.classify(observation)
    elif language == "java":
        classified = java.classify(observation)
    else:
        classified = None
    if classified is not None:
        return classified
    return classify_common(observation)


def classify_positive_candidate_rejection(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification:
    if _is_fixture_or_generated_path(observation.file_path):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("fixture_or_generated_path",),
        )
    if _is_inline_dynamic_chain(observation.identifier):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("inline_dynamic_call_chain",),
        )
    if _is_dynamic_terminal(observation.identifier):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("positive_candidate_dynamic_member_terminal",),
        )
    raw_drop_reason = observation.raw_drop_reason.strip()
    if (
        raw_drop_reason == "unique_without_provenance"
        and ".index." in observation.identifier
    ):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("runtime_composed_index_surface",),
        )
    if raw_drop_reason == "invalid_observation_shape":
        return DiagnosticClassification(
            bucket="likely_parser_extraction_gap",
            reasons=("positive_candidate_invalid_shape",),
        )
    if raw_drop_reason == "ambiguous_multiple_in_scope_candidates":
        return DiagnosticClassification(
            bucket="likely_unindexed_symbol",
            reasons=("positive_candidate_ambiguous",),
        )
    if raw_drop_reason == "ambiguous_no_in_scope_candidate":
        return DiagnosticClassification(
            bucket="likely_unindexed_symbol",
            reasons=("positive_candidate_out_of_scope_after_narrowing",),
        )
    if raw_drop_reason == "ambiguous_no_caller_module":
        return DiagnosticClassification(
            bucket="likely_unindexed_symbol",
            reasons=("positive_candidate_without_caller_module",),
        )
    if raw_drop_reason == "unique_without_provenance":
        return DiagnosticClassification(
            bucket="likely_unindexed_symbol",
            reasons=("positive_candidate_without_provenance",),
        )
    if raw_drop_reason == "no_candidates":
        return DiagnosticClassification(
            bucket="unclassified_no_in_repo_candidate",
            reasons=("positive_candidate_no_candidates",),
        )
    return DiagnosticClassification(
        bucket="likely_unindexed_symbol",
        reasons=("positive_candidate_rejected",),
    )
