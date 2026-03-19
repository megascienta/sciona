# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Types used by call extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from ...languages.common.ir import LocalBindingFact


@dataclass(frozen=True)
class CallExtractionRecord:
    """Artifact-stage callsite work item derived from observed callsite data."""

    caller_structural_id: str
    caller_qualified_name: str
    caller_node_type: str
    callee_identifiers: Sequence[str]
    local_binding_facts: Sequence["LocalBindingFact"] = ()


@dataclass(frozen=True)
class PrePersistObservation:
    """Diagnostic-only observation for one pre-persist miss."""

    identifier: str
    ordinal: int
    callee_kind: str
    caller_language: str | None = None
    caller_module: str | None = None
    candidate_module_hints: tuple[str, ...] = ()
    local_binding_symbol: str = ""
    local_binding_target: str = ""
    local_binding_kind: str = ""
    local_binding_evidence_kind: str = ""


@dataclass(frozen=True)
class TerminalCallIR:
    terminal: str


@dataclass(frozen=True)
class QualifiedCallIR:
    parts: tuple[str, ...]
    terminal: str


@dataclass(frozen=True)
class ReceiverCallIR:
    receiver_chain: tuple[str, ...]
    terminal: str


CallTargetIR = TerminalCallIR | QualifiedCallIR | ReceiverCallIR


@dataclass(frozen=True)
class CallTarget:
    """Captured call target text with terminal identifier."""

    terminal: str
    callee_text: str | None
    receiver: str | None = None
    receiver_chain: tuple[str, ...] = ()
    callee_kind: str = "unqualified"
    ir: CallTargetIR | None = None
    call_span: tuple[int, int] | None = None
    invocation_kind: str | None = None
    type_arguments: str | None = None
    argument_count: int | None = None


__all__ = [
    "CallExtractionRecord",
    "CallTarget",
    "CallTargetIR",
    "PrePersistObservation",
    "QualifiedCallIR",
    "ReceiverCallIR",
    "TerminalCallIR",
]
