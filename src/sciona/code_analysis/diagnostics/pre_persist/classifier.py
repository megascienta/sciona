# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Best-effort classification for rejected-call observations."""

from __future__ import annotations

from .languages import java, javascript, python, typescript
from .languages.common import classify_common
from .models import DiagnosticClassification, DiagnosticMissObservation


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
    raw_drop_reason = observation.raw_drop_reason.strip()
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
