# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java call extraction and resolution utilities."""

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


def callee_text(call_node, callee_node, content: bytes) -> str | None:
    if call_node is None:
        return node_text(callee_node, content)
    if call_node.type == "method_invocation":
        name_node = call_node.child_by_field_name("name")
        object_node = call_node.child_by_field_name("object")
        name = node_text(name_node or callee_node, content)
        if object_node is not None:
            obj = node_text(object_node, content)
            if obj and name:
                return f"{obj}.{name}"
        return name
    if call_node.type == "object_creation_expression":
        type_node = call_node.child_by_field_name("type")
        return node_text(type_node, content) or node_text(callee_node, content)
    return node_text(callee_node, content)


def resolve_java_calls(
    targets: List[CallTarget],
    module_name: str,
    module_functions: set[str],
    class_methods: dict[str, set[str]],
    class_name_map: dict[str, str],
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    static_wildcard_targets: set[str],
    class_name: str | None,
    instance_types: dict[str, str],
    module_prefix: str | None,
    qualify_java_type,
    *,
    outcome_diagnostics: dict[str, int] | None = None,
) -> List[str]:
    class_method_names = class_methods.get(class_name, set()) if class_name else set()
    requests = _to_requests(targets)
    adapter = _JavaCallAdapter(
        module_name=module_name,
        module_functions=module_functions,
        class_name=class_name,
        class_method_names=class_method_names,
        class_methods=class_methods,
        class_name_map=class_name_map,
        class_name_candidates=class_name_candidates,
        import_aliases=import_aliases,
        member_aliases=member_aliases,
        static_wildcard_targets=static_wildcard_targets,
        instance_types=instance_types,
        module_prefix=module_prefix,
        qualify_java_type=qualify_java_type,
    )
    validate_stage_order(adapter.stage_order)
    outcomes = resolve_with_adapter(requests, adapter)
    if outcome_diagnostics is not None:
        for provenance, count in summarize_outcome_provenance(outcomes).items():
            outcome_diagnostics[provenance] = outcome_diagnostics.get(provenance, 0) + count
    return materialize_outcomes(outcomes)


@dataclass(frozen=True)
class _JavaCallAdapter(CallResolutionAdapter):
    stage_order: ClassVar[tuple[str, ...]] = REQUIRED_RESOLUTION_STAGES
    module_name: str
    module_functions: set[str]
    class_name: str | None
    class_method_names: set[str]
    class_methods: dict[str, set[str]]
    class_name_map: dict[str, str]
    class_name_candidates: dict[str, set[str]]
    import_aliases: dict[str, str]
    member_aliases: dict[str, str]
    static_wildcard_targets: set[str]
    instance_types: dict[str, str]
    module_prefix: str | None
    qualify_java_type: object

    def resolve(self, request: CallResolutionRequest) -> List[CallResolutionOutcome]:
        terminal = request.terminal
        raw = request.callee_text
        receiver_hint = request.receiver
        receiver_symbol = _receiver_symbol(request, raw, receiver_hint)
        if receiver_symbol and receiver_symbol in self.instance_types:
            qualified_type = self.qualify_java_type(
                self.instance_types[receiver_symbol],
                self.module_name,
                self.class_name_candidates,
                self.import_aliases,
                self.module_prefix,
            )
            if qualified_type:
                return [_outcome(f"{qualified_type}.{terminal}", "module_scoped")]
        receiver, receiver_simple = _dotted_receiver(request, raw)
        if receiver is not None and receiver_simple is not None:
            if receiver_hint and receiver_simple != receiver_hint:
                receiver_simple = receiver_hint
            instance_type = self.instance_types.get(receiver_simple)
            if instance_type:
                qualified_type = self.qualify_java_type(
                    instance_type,
                    self.module_name,
                    self.class_name_candidates,
                    self.import_aliases,
                    self.module_prefix,
                )
                if qualified_type:
                    return [_outcome(f"{qualified_type}.{terminal}", "exact_qname")]
            if receiver_simple[:1].isupper():
                import_target = self.import_aliases.get(receiver_simple)
                local_class = _unique_class_candidate(
                    receiver_simple,
                    self.class_name_candidates,
                )
                if import_target:
                    return [_outcome(f"{import_target}.{terminal}", "import_narrowed")]
                if local_class:
                    return [_outcome(f"{local_class}.{terminal}", "exact_qname")]
        if is_unqualified_request(request):
            import_target = self.import_aliases.get(terminal)
            local_class = _unique_class_candidate(
                terminal,
                self.class_name_candidates,
            )
            if import_target:
                return [_outcome(f"{import_target}.{terminal}", "import_narrowed")]
            if local_class:
                return [_outcome(f"{local_class}.{terminal}", "exact_qname")]
            if terminal in self.member_aliases:
                return [_outcome(self.member_aliases[terminal], "import_narrowed")]
            if self.static_wildcard_targets:
                matched_targets = [
                    class_qname
                    for class_qname in sorted(self.static_wildcard_targets)
                    if terminal in self.class_methods.get(class_qname, set())
                ]
                if len(matched_targets) == 1:
                    return [_outcome(f"{matched_targets[0]}.{terminal}", "import_narrowed")]
                if len(self.static_wildcard_targets) == 1 and not matched_targets:
                    only = next(iter(self.static_wildcard_targets))
                    return [_outcome(f"{only}.{terminal}", "import_narrowed")]
        if self.class_name and terminal in self.class_method_names:
            if is_receiver_call_request(request) or is_unqualified_request(request):
                return [_outcome(f"{self.class_name}.{terminal}", "module_scoped")]
        if is_unqualified_request(request) and terminal in self.module_functions:
            return [_outcome(f"{self.module_name}.{terminal}", "module_scoped")]
        class_qualified = _unique_class_candidate(
            terminal,
            self.class_name_candidates,
        )
        if class_qualified and terminal in self.class_methods.get(class_qualified, set()):
            return [_outcome(f"{class_qualified}.{terminal}", "exact_qname")]
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


def is_unqualified(callee_text_raw: str) -> bool:
    return "." not in callee_text_raw


def is_receiver_call(callee_text_raw: str) -> bool:
    return callee_text_raw.startswith("this.") or callee_text_raw.startswith("super.")


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


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    text = getattr(node, "text", None)
    if text:
        return text.decode("utf-8")
    return content[node.start_byte : node.end_byte].decode("utf-8")


def _unique_class_candidate(
    simple_name: str,
    class_name_candidates: dict[str, set[str]],
) -> str | None:
    candidates = class_name_candidates.get(simple_name) or set()
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def _receiver_symbol(
    request: CallResolutionRequest,
    raw: str,
    receiver_hint: str | None,
) -> str | None:
    chain = request.receiver_chain
    if isinstance(request.ir, ReceiverCallIR):
        chain = request.ir.receiver_chain
    for token in reversed(chain):
        if token in {"this", "super"}:
            continue
        return token
    if receiver_hint:
        return receiver_hint
    if "." in raw:
        receiver = raw.rsplit(".", 1)[0].strip()
        return receiver.rsplit(".", 1)[-1]
    return None


def _dotted_receiver(
    request: CallResolutionRequest,
    raw: str,
) -> tuple[str | None, str | None]:
    if isinstance(request.ir, QualifiedCallIR):
        if len(request.ir.parts) < 2:
            return None, None
        receiver = ".".join(request.ir.parts[:-1])
        receiver_simple = request.ir.parts[-2] if len(request.ir.parts) >= 2 else None
        return receiver, receiver_simple
    if isinstance(request.ir, ReceiverCallIR):
        chain = request.ir.receiver_chain
        if not chain:
            return None, None
        receiver = ".".join(chain)
        receiver_simple = chain[-1]
        return receiver, receiver_simple
    if "." not in raw:
        return None, None
    receiver = raw.rsplit(".", 1)[0].strip()
    receiver_simple = receiver.rsplit(".", 1)[-1]
    return receiver, receiver_simple


def _outcome(candidate_qname: str, provenance: str) -> CallResolutionOutcome:
    return CallResolutionOutcome(candidate_qname=candidate_qname, provenance=provenance)
