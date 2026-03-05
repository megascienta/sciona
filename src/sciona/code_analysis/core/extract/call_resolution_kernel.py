# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared call-resolution kernel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from ...tools.call_extraction import CallTargetIR
from ....runtime.call_resolution_contract import (
    REQUIRED_RESOLUTION_STAGES,
    STAGE_ALIAS_NARROWING,
    STAGE_CLASS_SCOPED,
    STAGE_MODULE_SCOPED,
    STAGE_RECEIVER_TYPED,
)


MODE_SHARED = "shared"


@dataclass(frozen=True)
class CallResolutionRequest:
    """Normalized call target payload used by adapters."""

    terminal: str
    callee_text: str
    receiver: str | None = None
    receiver_chain: tuple[str, ...] = ()
    callee_kind: str = "unqualified"
    ir: CallTargetIR | None = None
    invocation_kind: str | None = None
    type_arguments: str | None = None


@dataclass(frozen=True)
class CallResolutionOutcome:
    """Resolved candidate with provenance metadata."""

    candidate_qname: str
    provenance: str


ALLOWED_MATERIALIZATION_PROVENANCE = frozenset(
    {"exact_qname", "module_scoped", "import_narrowed"}
)
# Adapters may emit provisional provenance labels (for example
# "ambiguous_candidate") for diagnostics; these are intentionally not in the
# materialization allow-list and are dropped by materialize_outcomes.
PROVENANCE_TERMINAL_FALLBACK = "terminal_fallback"


class CallResolutionAdapter(Protocol):
    """Adapter that resolves one call request into ordered candidates."""

    def resolve(self, request: CallResolutionRequest) -> Sequence[CallResolutionOutcome]:
        ...


def resolve_with_adapter(
    requests: Sequence[CallResolutionRequest],
    adapter: CallResolutionAdapter,
) -> list[CallResolutionOutcome]:
    """Resolve calls using ordered adapter candidates with terminal fallback."""

    resolved: list[CallResolutionOutcome] = []
    for request in requests:
        candidates = [candidate for candidate in adapter.resolve(request) if candidate]
        if candidates:
            resolved.append(candidates[0])
            continue
        resolved.append(
            CallResolutionOutcome(
                candidate_qname=request.terminal,
                provenance=PROVENANCE_TERMINAL_FALLBACK,
            )
        )
    return resolved


def materialize_outcomes(
    outcomes: Sequence[CallResolutionOutcome],
) -> list[str]:
    """Return stable identifier list for outcomes that pass provenance allow-list."""

    materialized: list[str] = []
    seen: set[str] = set()
    for outcome in outcomes:
        if outcome.provenance not in ALLOWED_MATERIALIZATION_PROVENANCE:
            continue
        candidate = (outcome.candidate_qname or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        materialized.append(candidate)
    return materialized


def summarize_outcome_provenance(
    outcomes: Sequence[CallResolutionOutcome],
) -> dict[str, int]:
    summary: dict[str, int] = {}
    for outcome in outcomes:
        summary[outcome.provenance] = summary.get(outcome.provenance, 0) + 1
    return summary


def validate_stage_order(stage_order: Sequence[str]) -> None:
    """Fail fast when an adapter diverges from the shared stage contract."""
    if tuple(stage_order) != REQUIRED_RESOLUTION_STAGES:
        raise ValueError(
            "call resolution stage order mismatch: "
            f"expected={REQUIRED_RESOLUTION_STAGES} got={tuple(stage_order)}"
        )


__all__ = [
    "CallResolutionAdapter",
    "CallResolutionOutcome",
    "CallResolutionRequest",
    "MODE_SHARED",
    "REQUIRED_RESOLUTION_STAGES",
    "PROVENANCE_TERMINAL_FALLBACK",
    "STAGE_ALIAS_NARROWING",
    "STAGE_CLASS_SCOPED",
    "STAGE_MODULE_SCOPED",
    "STAGE_RECEIVER_TYPED",
    "materialize_outcomes",
    "resolve_with_adapter",
    "summarize_outcome_provenance",
    "validate_stage_order",
]
