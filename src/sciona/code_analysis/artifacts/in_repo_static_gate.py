# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Single admissibility gate for durable in-repo static callsite rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from ..languages.common.contracts.loader import load_contract_json


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

_GATE_CONTRACT = load_contract_json("in_repo_static_gate.json")

ALLOWED_CALLSITE_PROVENANCE = frozenset(
    str(value)
    for value in (_GATE_CONTRACT.get("allowed_callsite_provenance") or [])
)
ALLOWED_CALLSITE_DROP_REASONS = frozenset(
    str(value)
    for value in (_GATE_CONTRACT.get("allowed_callsite_drop_reasons") or [])
)
ALLOWED_NON_ACCEPTED_GATE_REASONS = frozenset(
    str(value)
    for value in (_GATE_CONTRACT.get("allowed_non_accepted_gate_reasons") or [])
)


@dataclass(frozen=True)
class InRepoStaticGateDecision:
    persist: bool
    gate_reason: str | None = None
    raw_drop_reason: str | None = None


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
        return InRepoStaticGateDecision(
            False,
            gate_reason="no_in_repo_candidate",
            raw_drop_reason=drop_reason,
        )
    if status == "accepted":
        if not accepted_callee_id or drop_reason is not None:
            return InRepoStaticGateDecision(
                False,
                gate_reason="invalid_observation_shape",
                raw_drop_reason=drop_reason,
            )
        if provenance not in ALLOWED_CALLSITE_PROVENANCE:
            return InRepoStaticGateDecision(
                False,
                gate_reason="invalid_observation_shape",
            )
        if accepted_callee_id not in in_repo_callable_ids:
            return InRepoStaticGateDecision(
                False,
                gate_reason="outside_in_repo_scope",
            )
        return InRepoStaticGateDecision(True)
    if status == "dropped":
        if accepted_callee_id is not None or provenance is not None or drop_reason is None:
            return InRepoStaticGateDecision(
                False,
                gate_reason="invalid_observation_shape",
                raw_drop_reason=drop_reason,
            )
        if drop_reason not in ALLOWED_CALLSITE_DROP_REASONS:
            return InRepoStaticGateDecision(
                False,
                gate_reason="invalid_observation_shape",
                raw_drop_reason=drop_reason,
            )
        return InRepoStaticGateDecision(
            False,
            gate_reason="insufficient_static_evidence",
            raw_drop_reason=drop_reason,
        )
    return InRepoStaticGateDecision(
        False,
        gate_reason="invalid_observation_shape",
        raw_drop_reason=drop_reason,
    )


def normalized_non_accepted_gate_reason(bucket: str) -> str:
    if bucket not in ALLOWED_NON_ACCEPTED_GATE_REASONS:
        return "invalid_observation_shape"
    return bucket


__all__ = [
    "ALLOWED_CALLSITE_DROP_REASONS",
    "ALLOWED_CALLSITE_PROVENANCE",
    "ALLOWED_NON_ACCEPTED_GATE_REASONS",
    "CallsiteRow",
    "InRepoStaticGateDecision",
    "evaluate_callsite_row_for_persistence",
    "normalized_non_accepted_gate_reason",
]
