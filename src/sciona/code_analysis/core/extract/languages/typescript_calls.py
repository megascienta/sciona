# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript call resolution utilities."""

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

def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    text = getattr(node, "text", None)
    if text:
        return text.decode("utf-8")
    return content[node.start_byte : node.end_byte].decode("utf-8")


def callee_text(call_node, callee_node, content: bytes) -> str | None:
    if call_node is None:
        return node_text(callee_node, content)
    if call_node.type == "new_expression":
        constructor = (
            call_node.child_by_field_name("constructor")
            or call_node.child_by_field_name("type")
            or call_node.child_by_field_name("function")
        )
        return node_text(constructor or callee_node, content)
    return node_text(callee_node, content)


def resolve_typescript_calls(
    targets: List[CallTarget],
    module_name: str,
    module_functions: set[str],
    class_methods: dict[str, set[str]],
    class_name: str | None,
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    class_name_map: dict[str, str],
    class_name_candidates: dict[str, set[str]],
    instance_map: dict[str, str],
    class_instance_map: dict[str, dict[str, str]],
    *,
    outcome_diagnostics: dict[str, int] | None = None,
) -> List[str]:
    class_method_names = class_methods.get(class_name, set()) if class_name else set()
    requests = _to_requests(targets)
    adapter = _TypeScriptCallAdapter(
        module_name=module_name,
        module_functions=module_functions,
        class_name=class_name,
        class_method_names=class_method_names,
        import_aliases=import_aliases,
        member_aliases=member_aliases,
        class_name_map=class_name_map,
        class_name_candidates=class_name_candidates,
        instance_map=instance_map,
        class_instance_map=class_instance_map,
    )
    validate_stage_order(adapter.stage_order)
    outcomes = resolve_with_adapter(requests, adapter)
    if outcome_diagnostics is not None:
        for provenance, count in summarize_outcome_provenance(outcomes).items():
            outcome_diagnostics[provenance] = outcome_diagnostics.get(provenance, 0) + count
    return materialize_outcomes(outcomes)


@dataclass(frozen=True)
class _TypeScriptCallAdapter(CallResolutionAdapter):
    stage_order: ClassVar[tuple[str, ...]] = REQUIRED_RESOLUTION_STAGES
    module_name: str
    module_functions: set[str]
    class_name: str | None
    class_method_names: set[str]
    import_aliases: dict[str, str]
    member_aliases: dict[str, str]
    class_name_map: dict[str, str]
    class_name_candidates: dict[str, set[str]]
    instance_map: dict[str, str]
    class_instance_map: dict[str, dict[str, str]]

    def resolve(self, request: CallResolutionRequest) -> List[CallResolutionOutcome]:
        terminal = request.terminal
        callee_text = request.callee_text
        receiver = request.receiver
        chain_target = _resolve_receiver_chain_target(
            class_name=self.class_name,
            receiver_chain=receiver_chain_for_request(request),
            instance_map=self.instance_map,
            class_instance_map=self.class_instance_map,
        )
        if chain_target:
            return [_outcome(f"{chain_target}.{terminal}", "module_scoped")]
        head, rest, dotted_text = _dotted_parts(request)
        if head is not None and rest is not None and dotted_text is not None:
            if head in self.instance_map:
                return [_outcome(f"{self.instance_map[head]}.{terminal}", "exact_qname")]
            if head in self.class_name_map and head[:1].isupper():
                candidates = self.class_name_candidates.get(head) or set()
                if len(candidates) == 1:
                    return [
                        _outcome(f"{next(iter(candidates))}.{terminal}", "exact_qname")
                    ]
                return [_outcome(terminal, "ambiguous_candidate")]
            if self.class_name and (receiver == "this" or dotted_text.startswith("this.")):
                chain = receiver_chain_for_request(request)
                if len(chain) >= 2:
                    field = chain[1]
                    target_class = self.class_instance_map.get(self.class_name, {}).get(
                        field
                    )
                    if target_class:
                        return [_outcome(f"{target_class}.{terminal}", "module_scoped")]
            if head in self.import_aliases:
                return [_outcome(f"{self.import_aliases[head]}.{rest}", "import_narrowed")]
        if is_unqualified_request(request) and terminal in self.member_aliases:
            return [_outcome(self.member_aliases[terminal], "import_narrowed")]
        if (
            self.class_name
            and is_receiver_call_request(request)
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


def is_receiver_call(callee_text: str) -> bool:
    return callee_text.startswith("this.") or callee_text.startswith("super.")


def is_unqualified_request(request: CallResolutionRequest) -> bool:
    if isinstance(request.ir, TerminalCallIR):
        return True
    if isinstance(request.ir, (QualifiedCallIR, ReceiverCallIR)):
        return False
    return is_unqualified(request.callee_text)


def is_receiver_call_request(request: CallResolutionRequest) -> bool:
    if isinstance(request.ir, ReceiverCallIR):
        chain = request.ir.receiver_chain
        return bool(chain) and chain[0] in {"this", "super"}
    return is_receiver_call(request.callee_text)


def receiver_chain_for_request(request: CallResolutionRequest) -> tuple[str, ...]:
    if isinstance(request.ir, ReceiverCallIR):
        return request.ir.receiver_chain
    return request.receiver_chain


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
    *,
    class_name: str | None,
    receiver_chain: tuple[str, ...],
    instance_map: dict[str, str],
    class_instance_map: dict[str, dict[str, str]],
) -> str | None:
    if not receiver_chain:
        return None
    head = receiver_chain[0]
    if head in instance_map:
        return instance_map[head]
    if head not in {"this", "super"} or not class_name:
        return None
    current_class = class_name
    for field in receiver_chain[1:]:
        next_class = class_instance_map.get(current_class, {}).get(field)
        if not next_class:
            return None
        current_class = next_class
    return current_class


def _outcome(candidate_qname: str, provenance: str) -> CallResolutionOutcome:
    return CallResolutionOutcome(candidate_qname=candidate_qname, provenance=provenance)
