# SPDX-License-Identifier: MIT

"""Language-agnostic fallback classifier."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation


def classify_binding_backed_miss(
    observation: DiagnosticMissObservation,
    *,
    positive_candidate: bool,
) -> DiagnosticClassification | None:
    if not observation.local_binding_target:
        return None
    reason = (
        f"binding_backed_{observation.local_binding_kind}"
        if observation.local_binding_kind
        else "binding_backed_local_binding"
    )
    if positive_candidate:
        raw_drop_reason = observation.raw_drop_reason.strip()
        if raw_drop_reason == "ambiguous_multiple_in_scope_candidates":
            reason = f"{reason}_ambiguous"
        elif raw_drop_reason == "ambiguous_no_in_scope_candidate":
            reason = f"{reason}_out_of_scope_after_narrowing"
        elif raw_drop_reason == "unique_without_provenance":
            reason = f"{reason}_without_provenance"
        elif raw_drop_reason == "no_candidates":
            reason = f"{reason}_no_candidates"
    return DiagnosticClassification(
        bucket="unindexed_symbol_shape",
        reasons=(reason,),
    )


def classify_common(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification:
    identifier = observation.identifier.strip()
    terminal = identifier.rsplit(".", 1)[-1]
    if not identifier or not observation.file_path:
        return DiagnosticClassification(
            bucket="parser_extraction_mismatch",
            reasons=("missing_identifier_or_file_path",),
        )
    if _is_fixture_or_generated_path(observation.file_path):
        return DiagnosticClassification(
            bucket="dynamic_or_indirect_shape",
            reasons=("fixture_or_generated_path",),
        )
    if _has_repeated_qualified_segment(identifier):
        return DiagnosticClassification(
            bucket="parser_extraction_mismatch",
            reasons=("repeated_qualified_segment",),
        )
    if _has_inline_dynamic_call_chain(identifier):
        return DiagnosticClassification(
            bucket="dynamic_or_indirect_shape",
            reasons=("inline_dynamic_call_chain",),
        )
    if terminal in {"then", "catch", "finally"}:
        return DiagnosticClassification(
            bucket="dynamic_or_indirect_shape",
            reasons=("fluent_terminal",),
        )
    binding_backed = classify_binding_backed_miss(
        observation,
        positive_candidate=False,
    )
    if binding_backed is not None:
        return binding_backed
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
                    bucket="unindexed_symbol_shape",
                    reasons=("reachable_repo_owned_prefix",),
                )
            if observation.repo_hint_overlap:
                return DiagnosticClassification(
                    bucket="unindexed_symbol_shape",
                    reasons=("repo_hint_overlap",),
                )
            if repo_prefix_depth == 1:
                return DiagnosticClassification(
                    bucket="external_dependency_shape",
                    reasons=("shallow_non_reachable_repo_prefix",),
                )
            return DiagnosticClassification(
                bucket="unindexed_symbol_shape",
                reasons=("repo_owned_qualified_prefix",),
            )
        return DiagnosticClassification(
            bucket="dynamic_or_indirect_shape",
            reasons=("repo_owned_terminal_call_shape",),
        )
    if observation.local_binding_target:
        return DiagnosticClassification(
            bucket="unindexed_symbol_shape",
            reasons=("local_binding_target",),
        )
    if "." in identifier:
        first = identifier.split(".", 1)[0]
        if first in {"self", "this", "cls", "super"}:
            return DiagnosticClassification(
                bucket="dynamic_or_indirect_shape",
                reasons=("dynamic_receiver_root",),
            )
        if observation.repo_hint_overlap:
            return DiagnosticClassification(
                bucket="unindexed_symbol_shape",
                reasons=("repo_hint_overlap",),
            )
        if observation.candidate_module_hints:
            return DiagnosticClassification(
                bucket="external_dependency_shape",
                reasons=("qualified_identifier_with_external_module_hints",),
            )
        return DiagnosticClassification(
            bucket="external_dependency_shape",
            reasons=("qualified_identifier_without_repo_candidate",),
        )
    return DiagnosticClassification(
        bucket="unindexed_symbol_shape",
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


def _has_inline_dynamic_call_chain(identifier: str) -> bool:
    return "." in identifier and any(token in identifier for token in ("(", "[", "]"))


def _is_fixture_or_generated_path(file_path: str) -> bool:
    parts = [segment.lower() for segment in file_path.replace("\\", "/").split("/") if segment]
    if not parts:
        return False
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
