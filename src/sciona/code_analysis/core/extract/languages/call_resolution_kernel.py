# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared call-resolution kernel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

from ....tools.call_extraction import CallTargetIR


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
                provenance="terminal_fallback",
            )
        )
    return resolved


def materialize_outcomes(
    outcomes: Sequence[CallResolutionOutcome],
    *,
    allowed_provenance: Sequence[str] = tuple(ALLOWED_MATERIALIZATION_PROVENANCE),
) -> list[str]:
    """Return stable identifier list for outcomes that pass provenance allow-list."""

    allowed = set(allowed_provenance)
    materialized: list[str] = []
    seen: set[str] = set()
    for outcome in outcomes:
        if outcome.provenance not in allowed:
            continue
        candidate = (outcome.candidate_qname or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        materialized.append(candidate)
    return materialized


def resolve_with_mode(
    *,
    shared_resolver: Callable[[], list[str]],
) -> list[str]:
    """Resolve calls using the shared deterministic resolver path."""
    return shared_resolver()


__all__ = [
    "CallResolutionAdapter",
    "CallResolutionOutcome",
    "CallResolutionRequest",
    "MODE_SHARED",
    "materialize_outcomes",
    "resolve_with_adapter",
    "resolve_with_mode",
]
