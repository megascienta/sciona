# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Single admissibility gate for durable in-repo static callsite rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


CallsiteRow: TypeAlias = tuple[
    str,
    str,
    str | None,
    str | None,
    str | None,
    int,
    str,
    int | None,
    int | None,
    int,
    int | None,
    str | None,
]

ALLOWED_CALLSITE_PROVENANCE = frozenset(
    {"exact_qname", "module_scoped", "import_narrowed", "export_chain_narrowed"}
)
ALLOWED_CALLSITE_DROP_REASONS = frozenset(
    {
        "no_candidates",
        "unique_without_provenance",
        "ambiguous_no_caller_module",
        "ambiguous_no_in_scope_candidate",
        "ambiguous_multiple_in_scope_candidates",
    }
)
ALLOWED_PRE_PERSIST_FILTER_BUCKETS = frozenset(
    {
        "no_in_repo_candidate",
        "accepted_outside_in_repo",
        "invalid_observation_shape",
    }
)


@dataclass(frozen=True)
class InRepoStaticGateDecision:
    persist: bool
    rejection_bucket: str | None = None


def evaluate_callsite_row_for_persistence(
    row: CallsiteRow,
    *,
    in_repo_callable_ids: set[str],
) -> InRepoStaticGateDecision:
    (
        _identifier,
        status,
        accepted_callee_id,
        provenance,
        drop_reason,
        candidate_count,
        _callee_kind,
        _call_start_byte,
        _call_end_byte,
        _call_ordinal,
        _in_scope_candidate_count,
        _candidate_module_hints,
    ) = row
    if candidate_count <= 0:
        return InRepoStaticGateDecision(False, "no_in_repo_candidate")
    if status == "accepted":
        if not accepted_callee_id or drop_reason is not None:
            return InRepoStaticGateDecision(False, "invalid_observation_shape")
        if provenance not in ALLOWED_CALLSITE_PROVENANCE:
            return InRepoStaticGateDecision(False, "invalid_observation_shape")
        if accepted_callee_id not in in_repo_callable_ids:
            return InRepoStaticGateDecision(False, "accepted_outside_in_repo")
        return InRepoStaticGateDecision(True)
    if status == "dropped":
        if accepted_callee_id is not None or provenance is not None or drop_reason is None:
            return InRepoStaticGateDecision(False, "invalid_observation_shape")
        if drop_reason not in ALLOWED_CALLSITE_DROP_REASONS:
            return InRepoStaticGateDecision(False, "invalid_observation_shape")
        return InRepoStaticGateDecision(True)
    return InRepoStaticGateDecision(False, "invalid_observation_shape")


def normalized_pre_persist_bucket(bucket: str) -> str:
    if bucket not in ALLOWED_PRE_PERSIST_FILTER_BUCKETS:
        return "invalid_observation_shape"
    return bucket


__all__ = [
    "ALLOWED_CALLSITE_DROP_REASONS",
    "ALLOWED_CALLSITE_PROVENANCE",
    "ALLOWED_PRE_PERSIST_FILTER_BUCKETS",
    "CallsiteRow",
    "InRepoStaticGateDecision",
    "evaluate_callsite_row_for_persistence",
    "normalized_pre_persist_bucket",
]
