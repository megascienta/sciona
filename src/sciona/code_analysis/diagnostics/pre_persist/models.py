# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Diagnostic-only models for pre-persist miss classification."""

from __future__ import annotations

from dataclasses import dataclass, field


DIAGNOSTIC_BUCKET_KEYS = (
    "likely_external_dependency",
    "likely_standard_library_or_builtin",
    "likely_dynamic_dispatch_or_indirect",
    "likely_unindexed_symbol",
    "likely_parser_extraction_gap",
    "unclassified_no_in_repo_candidate",
    "accepted_outside_in_repo",
    "invalid_observation_shape",
)


@dataclass(frozen=True)
class DiagnosticMissObservation:
    language: str
    file_path: str
    caller_structural_id: str
    caller_qualified_name: str
    caller_module: str | None
    identifier: str
    ordinal: int
    callee_kind: str
    candidate_module_hints: tuple[str, ...] = ()
    repo_prefix_matches: tuple[str, ...] = ()
    longest_repo_prefix_match: str = ""
    repo_prefix_match_depth: int = 0
    identifier_root: str = ""


@dataclass(frozen=True)
class DiagnosticClassification:
    bucket: str
    reasons: tuple[str, ...] = ()


@dataclass
class DiagnosticAggregation:
    totals: dict[str, int] = field(default_factory=dict)
    by_language: dict[str, dict[str, int]] = field(default_factory=dict)
    by_scope: dict[str, dict[str, int]] = field(default_factory=dict)
    observations: list[dict[str, object]] = field(default_factory=list)
