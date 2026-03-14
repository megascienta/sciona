# SPDX-License-Identifier: MIT

"""Language-agnostic fallback classifier."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation


def classify_common(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification:
    identifier = observation.identifier.strip()
    if not identifier or not observation.file_path:
        return DiagnosticClassification(
            bucket="likely_parser_extraction_gap",
            reasons=("missing_identifier_or_file_path",),
        )
    if _has_repeated_qualified_segment(identifier):
        return DiagnosticClassification(
            bucket="likely_parser_extraction_gap",
            reasons=("repeated_qualified_segment",),
        )
    if observation.repo_prefix_matches:
        if observation.callee_kind == "qualified":
            repo_prefix_depth = observation.repo_prefix_match_depth or len(
                observation.repo_prefix_matches
            )
            if (
                observation.reachable_repo_prefix_matches
                or observation.reachable_repo_binding
            ):
                return DiagnosticClassification(
                    bucket="likely_unindexed_symbol",
                    reasons=("reachable_repo_owned_prefix",),
                )
            if observation.repo_hint_overlap:
                return DiagnosticClassification(
                    bucket="likely_unindexed_symbol",
                    reasons=("repo_hint_overlap",),
                )
            if repo_prefix_depth == 1:
                return DiagnosticClassification(
                    bucket="likely_external_dependency",
                    reasons=("shallow_non_reachable_repo_prefix",),
                )
            return DiagnosticClassification(
                bucket="likely_unindexed_symbol",
                reasons=("repo_owned_qualified_prefix",),
            )
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("repo_owned_terminal_call_shape",),
        )
    if "." in identifier:
        first = identifier.split(".", 1)[0]
        if first in {"self", "this", "cls", "super"}:
            return DiagnosticClassification(
                bucket="likely_dynamic_dispatch_or_indirect",
                reasons=("dynamic_receiver_root",),
            )
        if observation.repo_hint_overlap:
            return DiagnosticClassification(
                bucket="likely_unindexed_symbol",
                reasons=("repo_hint_overlap",),
            )
        if observation.candidate_module_hints:
            return DiagnosticClassification(
                bucket="likely_external_dependency",
                reasons=("qualified_identifier_with_external_module_hints",),
            )
        return DiagnosticClassification(
            bucket="likely_external_dependency",
            reasons=("qualified_identifier_without_repo_candidate",),
        )
    return DiagnosticClassification(
        bucket="likely_unindexed_symbol",
        reasons=("terminal_identifier_without_repo_candidate",),
    )


def _has_repeated_qualified_segment(identifier: str) -> bool:
    parts = [part for part in identifier.split(".") if part]
    if len(parts) < 2:
        return False
    for previous, current in zip(parts, parts[1:]):
        if previous == current:
            return True
    if len(parts) >= 3 and parts[-1] == parts[-3]:
        return True
    if len(parts) >= 4 and parts[-2:] == parts[-4:-2]:
        return True
    return False
