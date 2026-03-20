# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Diagnostic-only models for pre-persist miss classification."""

from __future__ import annotations

from dataclasses import dataclass, field


DIAGNOSTIC_BUCKET_KEYS = (
    "external_dependency_shape",
    "builtin_or_standard_shape",
    "dynamic_or_indirect_shape",
    "unindexed_symbol_shape",
    "parser_extraction_mismatch",
    "no_clear_in_repo_target",
    "outside_in_repo_scope",
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
    reachable_repo_prefix_matches: tuple[str, ...] = ()
    longest_reachable_repo_prefix_match: str = ""
    reachable_repo_binding: bool = False
    repo_hint_overlap: tuple[str, ...] = ()
    identifier_root: str = ""
    local_binding_symbol: str = ""
    local_binding_target: str = ""
    local_binding_kind: str = ""
    local_binding_evidence_kind: str = ""
    gate_reason: str = ""
    raw_drop_reason: str = ""


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
