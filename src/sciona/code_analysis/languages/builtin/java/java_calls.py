# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java call extraction and resolution utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, List

from ...common.ir import LocalBindingFact, binding_candidate_qnames_for_identifier
from ....tools.call_extraction import (
    CallTarget,
    QualifiedCallIR,
    ReceiverCallIR,
    TerminalCallIR,
)
from ...common.support.shared import node_text
from ....core.extract.call_resolution_kernel import (
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
    class_method_overloads: dict[str, dict[str, dict[int, set[str]]]],
    class_ancestors: dict[str, tuple[str, ...]],
    class_kind_map: dict[str, str],
    class_name_map: dict[str, str],
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    static_wildcard_targets: set[str],
    class_name: str | None,
    instance_types: dict[str, str],
    module_prefix: str | None,
    qualify_java_type,
    local_binding_facts: tuple[LocalBindingFact, ...] | list[LocalBindingFact] = (),
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
        class_method_overloads=class_method_overloads,
        class_ancestors=class_ancestors,
        class_kind_map=class_kind_map,
        class_name_map=class_name_map,
        class_name_candidates=class_name_candidates,
        import_aliases=import_aliases,
        member_aliases=member_aliases,
        static_wildcard_targets=static_wildcard_targets,
        instance_types=instance_types,
        module_prefix=module_prefix,
        qualify_java_type=qualify_java_type,
        local_binding_facts=tuple(local_binding_facts),
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
    class_method_overloads: dict[str, dict[str, dict[int, set[str]]]]
    class_ancestors: dict[str, tuple[str, ...]]
    class_kind_map: dict[str, str]
    class_name_map: dict[str, str]
    class_name_candidates: dict[str, set[str]]
    import_aliases: dict[str, str]
    member_aliases: dict[str, str]
    static_wildcard_targets: set[str]
    instance_types: dict[str, str]
    module_prefix: str | None
    qualify_java_type: object
    local_binding_facts: tuple[LocalBindingFact, ...]

    def resolve(self, request: CallResolutionRequest) -> List[CallResolutionOutcome]:
        terminal = request.terminal
        raw = request.callee_text
        receiver_hint = request.receiver
        argument_count = request.argument_count
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
                resolved_target = _resolve_from_lineage(
                    qualified_type,
                    terminal,
                    argument_count,
                    self.class_methods,
                    self.class_method_overloads,
                    self.class_ancestors,
                    self.class_kind_map,
                    self.class_name_candidates,
                )
                if resolved_target:
                    return [_outcome(resolved_target, "module_scoped")]
        receiver, receiver_simple = _dotted_receiver(request, raw)
        if receiver is not None and receiver_simple is not None:
            binding_outcomes = _binding_fact_outcomes(
                raw,
                self.local_binding_facts,
            )
            if binding_outcomes:
                return binding_outcomes
            qualified_receiver = self.qualify_java_type(
                receiver,
                self.module_name,
                self.class_name_candidates,
                self.import_aliases,
                self.module_prefix,
            )
            if qualified_receiver:
                resolved_target = _resolve_from_lineage(
                    qualified_receiver,
                    terminal,
                    argument_count,
                    self.class_methods,
                    self.class_method_overloads,
                    self.class_ancestors,
                    self.class_kind_map,
                    self.class_name_candidates,
                )
                if resolved_target:
                    return [_outcome(resolved_target, "exact_qname")]
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
                    resolved_target = _resolve_from_lineage(
                        qualified_type,
                        terminal,
                        argument_count,
                        self.class_methods,
                        self.class_method_overloads,
                        self.class_ancestors,
                        self.class_kind_map,
                        self.class_name_candidates,
                    )
                    if resolved_target:
                        return [_outcome(resolved_target, "exact_qname")]
            if receiver_simple[:1].isupper():
                import_target = self.import_aliases.get(receiver_simple)
                local_class = _unique_class_candidate(
                    receiver_simple,
                    self.class_name_candidates,
                )
                if import_target:
                    resolved_target = _resolve_from_lineage(
                        import_target,
                        terminal,
                        argument_count,
                        self.class_methods,
                        self.class_method_overloads,
                        self.class_ancestors,
                        self.class_kind_map,
                        self.class_name_candidates,
                    )
                    if resolved_target:
                        return [_outcome(resolved_target, "import_narrowed")]
                    return [
                        _outcome(
                            _resolved_method_target(
                                import_target,
                                terminal,
                                argument_count,
                                self.class_method_overloads,
                            ),
                            "import_narrowed",
                        )
                    ]
                if local_class:
                    resolved_target = _resolve_from_lineage(
                        local_class,
                        terminal,
                        argument_count,
                        self.class_methods,
                        self.class_method_overloads,
                        self.class_ancestors,
                        self.class_kind_map,
                        self.class_name_candidates,
                    )
                    if resolved_target:
                        return [_outcome(resolved_target, "exact_qname")]
        if is_unqualified_request(request):
            binding_outcomes = _binding_fact_outcomes(
                terminal,
                self.local_binding_facts,
            )
            if binding_outcomes:
                return binding_outcomes
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
                    resolved_target = _resolve_from_lineage(
                        matched_targets[0],
                        terminal,
                        argument_count,
                        self.class_methods,
                        self.class_method_overloads,
                        self.class_ancestors,
                        self.class_kind_map,
                        self.class_name_candidates,
                    )
                    if resolved_target:
                        return [_outcome(resolved_target, "import_narrowed")]
                narrowed_targets = _narrow_owners_by_arity(
                    matched_targets,
                    terminal,
                    argument_count,
                    self.class_method_overloads,
                )
                if len(narrowed_targets) == 1:
                    resolved_target = _resolve_from_lineage(
                        narrowed_targets[0],
                        terminal,
                        argument_count,
                        self.class_methods,
                        self.class_method_overloads,
                        self.class_ancestors,
                        self.class_kind_map,
                        self.class_name_candidates,
                    )
                    if resolved_target:
                        return [_outcome(resolved_target, "import_narrowed")]
                if len(self.static_wildcard_targets) == 1 and not matched_targets:
                    only = next(iter(self.static_wildcard_targets))
                    resolved_target = _resolve_from_lineage(
                        only,
                        terminal,
                        argument_count,
                        self.class_methods,
                        self.class_method_overloads,
                        self.class_ancestors,
                        self.class_kind_map,
                        self.class_name_candidates,
                    )
                    if resolved_target:
                        return [_outcome(resolved_target, "import_narrowed")]
                    return [
                        _outcome(
                            _resolved_method_target(
                                only,
                                terminal,
                                argument_count,
                                self.class_method_overloads,
                            ),
                            "import_narrowed",
                        )
                    ]
        if self.class_name and (is_receiver_call_request(request) or is_unqualified_request(request)):
            resolved_target = _resolve_from_lineage(
                self.class_name,
                terminal,
                argument_count,
                self.class_methods,
                self.class_method_overloads,
                self.class_ancestors,
                self.class_kind_map,
                self.class_name_candidates,
            )
            if resolved_target:
                return [_outcome(resolved_target, "module_scoped")]
        if is_unqualified_request(request) and terminal in self.module_functions:
            return [_outcome(f"{self.module_name}.{terminal}", "module_scoped")]
        class_qualified = _unique_class_candidate(
            terminal,
            self.class_name_candidates,
        )
        if class_qualified and terminal in self.class_methods.get(class_qualified, set()):
            resolved_target = _resolve_from_lineage(
                class_qualified,
                terminal,
                argument_count,
                self.class_methods,
                self.class_method_overloads,
                self.class_ancestors,
                self.class_kind_map,
                self.class_name_candidates,
            )
            if resolved_target:
                return [_outcome(resolved_target, "exact_qname")]
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
            argument_count=target.argument_count,
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


def _unique_class_candidate(
    simple_name: str,
    class_name_candidates: dict[str, set[str]],
) -> str | None:
    candidates = class_name_candidates.get(simple_name) or set()
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def _resolved_method_target(
    class_qname: str,
    terminal: str,
    argument_count: int | None,
    class_method_overloads: dict[str, dict[str, dict[int, set[str]]]],
) -> str:
    if argument_count is None:
        return f"{class_qname}.{terminal}"
    overloads = class_method_overloads.get(class_qname, {}).get(terminal, {})
    matched = overloads.get(argument_count) or set()
    if len(matched) == 1:
        return next(iter(sorted(matched)))
    return f"{class_qname}.{terminal}"


def _resolve_from_lineage(
    class_qname: str,
    terminal: str,
    argument_count: int | None,
    class_methods: dict[str, set[str]],
    class_method_overloads: dict[str, dict[str, dict[int, set[str]]]],
    class_ancestors: dict[str, tuple[str, ...]],
    class_kind_map: dict[str, str],
    class_name_candidates: dict[str, set[str]],
) -> str | None:
    owners_by_depth: dict[int, list[str]] = {}
    lineage = (class_qname, *class_ancestors.get(class_qname, ()))
    for depth, owner in enumerate(lineage):
        if terminal not in class_methods.get(owner, set()):
            continue
        owners_by_depth.setdefault(depth, []).append(owner)
    if not owners_by_depth:
        if (
            (
                class_qname in class_kind_map
                or class_qname in class_methods
                or class_qname in class_ancestors
                or any(
                    class_qname in candidates
                    for candidates in class_name_candidates.values()
                )
            )
            and class_kind_map.get(class_qname) == "enum"
            and terminal in {"values", "valueOf"}
        ):
            return _resolved_method_target(
                class_qname,
                terminal,
                argument_count,
                class_method_overloads,
            )
        return None
    all_owners = [
        owner
        for depth in sorted(owners_by_depth)
        for owner in owners_by_depth[depth]
    ]
    narrowed_all = _narrow_owners_by_arity(
        all_owners,
        terminal,
        argument_count,
        class_method_overloads,
    )
    if len(narrowed_all) == 1:
        return _resolved_method_target(
            narrowed_all[0],
            terminal,
            argument_count,
            class_method_overloads,
        )
    nearest_depth = min(owners_by_depth)
    owners = owners_by_depth[nearest_depth]
    if len(owners) != 1:
        narrowed = _narrow_owners_by_arity(
            owners,
            terminal,
            argument_count,
            class_method_overloads,
        )
        if len(narrowed) != 1:
            return None
        owners = narrowed
    return _resolved_method_target(
        owners[0],
        terminal,
        argument_count,
        class_method_overloads,
    )


def _narrow_owners_by_arity(
    owners: list[str],
    terminal: str,
    argument_count: int | None,
    class_method_overloads: dict[str, dict[str, dict[int, set[str]]]],
) -> list[str]:
    if argument_count is None:
        return owners
    narrowed: list[str] = []
    for owner in owners:
        overloads = class_method_overloads.get(owner, {}).get(terminal, {})
        if not overloads:
            narrowed.append(owner)
            continue
        if argument_count in overloads:
            narrowed.append(owner)
    return narrowed


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


def _binding_fact_outcomes(
    identifier: str,
    local_binding_facts: tuple[LocalBindingFact, ...],
) -> list[CallResolutionOutcome]:
    candidates = binding_candidate_qnames_for_identifier(identifier, local_binding_facts)
    if len(candidates) != 1:
        return []
    provenance = "exact_qname" if "." in identifier else "import_narrowed"
    return [_outcome(candidates[0], provenance)]


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
