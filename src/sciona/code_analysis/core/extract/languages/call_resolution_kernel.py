# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared call-resolution kernel and mode controls."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence


CALL_RESOLUTION_MODE_ENV = "SCIONA_CALL_RESOLUTION_MODE"
CALL_RESOLUTION_STRICT_COMPARE_ENV = "SCIONA_CALL_RESOLUTION_STRICT_COMPARE"
MODE_LEGACY = "legacy"
MODE_SHARED = "shared"
MODE_COMPARE = "compare"
VALID_MODES = {MODE_LEGACY, MODE_SHARED, MODE_COMPARE}


@dataclass(frozen=True)
class CallResolutionRequest:
    """Normalized call target payload used by adapters."""

    terminal: str
    callee_text: str
    receiver: str | None = None
    receiver_chain: tuple[str, ...] = ()
    callee_kind: str = "unqualified"


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
    legacy_resolver: Callable[[], list[str]] | None = None,
) -> list[str]:
    """Dispatch between legacy/shared resolvers and optional compare mode."""

    mode = os.getenv(CALL_RESOLUTION_MODE_ENV, MODE_SHARED).strip().lower()
    if mode not in VALID_MODES:
        mode = MODE_SHARED
    if mode == MODE_LEGACY and legacy_resolver is not None:
        return legacy_resolver()
    shared = shared_resolver()
    if mode == MODE_SHARED:
        return shared
    if legacy_resolver is None:
        return shared
    legacy = legacy_resolver()
    if shared != legacy and _strict_compare():
        raise RuntimeError(
            "call resolution mismatch between shared and legacy resolvers"
        )
    return legacy


def _strict_compare() -> bool:
    value = os.getenv(CALL_RESOLUTION_STRICT_COMPARE_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


__all__ = [
    "CALL_RESOLUTION_MODE_ENV",
    "CALL_RESOLUTION_STRICT_COMPARE_ENV",
    "CallResolutionAdapter",
    "CallResolutionOutcome",
    "CallResolutionRequest",
    "MODE_COMPARE",
    "MODE_LEGACY",
    "MODE_SHARED",
    "materialize_outcomes",
    "resolve_with_adapter",
    "resolve_with_mode",
]
