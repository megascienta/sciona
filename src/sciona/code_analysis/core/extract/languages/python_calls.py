# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python call resolution utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, List

from ....tools.call_extraction import (
    CallTarget,
    QualifiedCallIR,
    ReceiverCallIR,
    TerminalCallIR,
)
from .call_resolution_kernel import (
    CallResolutionAdapter,
    CallResolutionOutcome,
    CallResolutionRequest,
    REQUIRED_RESOLUTION_STAGES,
    materialize_outcomes,
    resolve_with_adapter,
    summarize_outcome_provenance,
    validate_stage_order,
)


def _receiver_field(callee_text: str) -> str | None:
    parts = callee_text.split(".")
    if len(parts) < 2:
        return None
    return parts[1]


def resolve_python_calls(
    targets: List[CallTarget],
    module_name: str,
    module_functions: set[str],
    class_methods: dict[str, set[str]],
    class_name: str | None,
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
    instance_map: dict[str, str],
    class_name_candidates: dict[str, set[str]],
    *,
    outcome_diagnostics: dict[str, int] | None = None,
    ambiguous_candidates: set[str] | None = None,
) -> List[str]:
    class_method_names = class_methods.get(class_name, set()) if class_name else set()
    requests = _to_requests(targets)
    adapter = _PythonCallAdapter(
        module_name=module_name,
        module_functions=module_functions,
        class_name=class_name,
        class_method_names=class_method_names,
        import_aliases=import_aliases,
        member_aliases=member_aliases,
        raw_module_map=raw_module_map,
        instance_map=instance_map,
        class_name_candidates=class_name_candidates,
    )
    validate_stage_order(adapter.stage_order)

    outcomes = resolve_with_adapter(requests, adapter)
    if ambiguous_candidates is not None:
        for outcome in outcomes:
            if outcome.provenance == "ambiguous_candidate" and outcome.candidate_qname:
                ambiguous_candidates.add(outcome.candidate_qname)
    if outcome_diagnostics is not None:
        for provenance, count in summarize_outcome_provenance(outcomes).items():
            outcome_diagnostics[provenance] = outcome_diagnostics.get(provenance, 0) + count
    return materialize_outcomes(outcomes)


@dataclass(frozen=True)
class _PythonCallAdapter(CallResolutionAdapter):
    stage_order: ClassVar[tuple[str, ...]] = REQUIRED_RESOLUTION_STAGES
    module_name: str
    module_functions: set[str]
    class_name: str | None
    class_method_names: set[str]
    import_aliases: dict[str, str]
    member_aliases: dict[str, str]
    raw_module_map: dict[str, str]
    instance_map: dict[str, str]
    class_name_candidates: dict[str, set[str]]

    def resolve(self, request: CallResolutionRequest) -> List[CallResolutionOutcome]:
        terminal = request.terminal
        callee_text = request.callee_text
        receiver = request.receiver
        receiver_target = _resolve_receiver_chain_target(
            request.receiver_chain, self.instance_map
        )
        if receiver_target:
            return [_outcome(f"{receiver_target}.{terminal}", "module_scoped")]
        head, rest, dotted_text = _dotted_parts(request)
        if head is not None and rest is not None and dotted_text is not None:
            if head in self.instance_map:
                return [_outcome(f"{self.instance_map[head]}.{terminal}", "exact_qname")]
            if receiver in {"self", "cls"} or head in {"self", "cls"}:
                field = _receiver_field(dotted_text)
                if field and field in self.instance_map:
                    return [
                        _outcome(f"{self.instance_map[field]}.{terminal}", "module_scoped")
                    ]
            if head in self.import_aliases:
                return [_outcome(f"{self.import_aliases[head]}.{rest}", "import_narrowed")]
            class_candidates = self.class_name_candidates.get(head) or set()
            if len(class_candidates) == 1:
                return [
                    _outcome(f"{next(iter(class_candidates))}.{terminal}", "exact_qname")
                ]
            if len(class_candidates) > 1:
                return [_outcome(terminal, "ambiguous_candidate")]
            for raw, normalized in self.raw_module_map.items():
                if dotted_text == raw or dotted_text.startswith(f"{raw}."):
                    suffix = dotted_text[len(raw) :].lstrip(".")
                    return [
                        _outcome(
                            f"{normalized}.{suffix}" if suffix else normalized,
                            "import_narrowed",
                        )
                    ]
        if is_unqualified_request(request) and terminal in self.member_aliases:
            return [_outcome(self.member_aliases[terminal], "import_narrowed")]
        if (
            self.class_name
            and is_self_receiver_request(request)
            and terminal in self.class_method_names
        ):
            return [_outcome(f"{self.class_name}.{terminal}", "module_scoped")]
        if is_unqualified_request(request) and terminal in self.module_functions:
            return [_outcome(f"{self.module_name}.{terminal}", "module_scoped")]
        return []


def _to_requests(targets: List[CallTarget]) -> list[CallResolutionRequest]:
    return [
        CallResolutionRequest(
            terminal=target.terminal,
            callee_text=(target.callee_text or "").strip(),
            receiver=target.receiver,
            receiver_chain=target.receiver_chain,
            callee_kind=target.callee_kind,
            ir=target.ir,
            invocation_kind=target.invocation_kind,
            type_arguments=target.type_arguments,
        )
        for target in targets
    ]


def is_unqualified(callee_text: str) -> bool:
    return "." not in callee_text


def is_self_receiver(callee_text: str) -> bool:
    return callee_text.startswith("self.") or callee_text.startswith("cls.")


def is_unqualified_request(request: CallResolutionRequest) -> bool:
    if isinstance(request.ir, TerminalCallIR):
        return True
    if isinstance(request.ir, (QualifiedCallIR, ReceiverCallIR)):
        return False
    return is_unqualified(request.callee_text)


def is_self_receiver_request(request: CallResolutionRequest) -> bool:
    if isinstance(request.ir, ReceiverCallIR):
        chain = request.ir.receiver_chain
        return bool(chain) and chain[0] in {"self", "cls"}
    return is_self_receiver(request.callee_text)


def _dotted_parts(
    request: CallResolutionRequest,
) -> tuple[str | None, str | None, str | None]:
    if isinstance(request.ir, QualifiedCallIR):
        if len(request.ir.parts) < 2:
            return None, None, None
        head = request.ir.parts[0]
        rest = ".".join(request.ir.parts[1:])
        return head, rest, ".".join(request.ir.parts)
    if isinstance(request.ir, ReceiverCallIR):
        chain = request.ir.receiver_chain
        if not chain:
            return None, None, None
        head = chain[0]
        rest = ".".join((*chain[1:], request.terminal))
        return head, rest, ".".join((*chain, request.terminal))
    if "." not in request.callee_text:
        return None, None, None
    head, rest = request.callee_text.split(".", 1)
    return head, rest, request.callee_text


def _resolve_receiver_chain_target(
    chain: tuple[str, ...],
    instance_map: dict[str, str],
) -> str | None:
    if not chain:
        return None
    if chain[0] in {"self", "cls"}:
        for token in chain[1:]:
            if token in instance_map:
                return instance_map[token]
        return None
    for token in chain:
        if token in instance_map:
            return instance_map[token]
    return None


def _outcome(candidate_qname: str, provenance: str) -> CallResolutionOutcome:
    return CallResolutionOutcome(candidate_qname=candidate_qname, provenance=provenance)
