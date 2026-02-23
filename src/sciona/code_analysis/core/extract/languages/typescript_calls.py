# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript call resolution utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ....tools.call_extraction import CallTarget
from .call_resolution_kernel import (
    CallResolutionAdapter,
    CallResolutionOutcome,
    CallResolutionRequest,
    materialize_outcomes,
    resolve_with_adapter,
    resolve_with_mode,
)


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
    return resolve_with_mode(
        shared_resolver=lambda: materialize_outcomes(resolve_with_adapter(requests, adapter)),
    )


@dataclass(frozen=True)
class _TypeScriptCallAdapter(CallResolutionAdapter):
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
            receiver_chain=request.receiver_chain,
            instance_map=self.instance_map,
            class_instance_map=self.class_instance_map,
        )
        if chain_target:
            return [_outcome(f"{chain_target}.{terminal}", "module_scoped")]
        if "." in callee_text:
            head, rest = callee_text.split(".", 1)
            if head in self.instance_map:
                return [_outcome(f"{self.instance_map[head]}.{terminal}", "exact_qname")]
            if head in self.class_name_map and head[:1].isupper():
                candidates = self.class_name_candidates.get(head) or set()
                if len(candidates) == 1:
                    return [
                        _outcome(f"{next(iter(candidates))}.{terminal}", "exact_qname")
                    ]
                return []
            if self.class_name and (receiver == "this" or callee_text.startswith("this.")):
                chain = request.receiver_chain
                if len(chain) >= 2:
                    field = chain[1]
                    target_class = self.class_instance_map.get(self.class_name, {}).get(
                        field
                    )
                    if target_class:
                        return [_outcome(f"{target_class}.{terminal}", "module_scoped")]
            if head in self.import_aliases:
                return [_outcome(f"{self.import_aliases[head]}.{rest}", "import_narrowed")]
        if terminal in self.member_aliases:
            return [_outcome(self.member_aliases[terminal], "import_narrowed")]
        if (
            self.class_name
            and is_receiver_call(callee_text)
            and terminal in self.class_method_names
        ):
            return [_outcome(f"{self.class_name}.{terminal}", "module_scoped")]
        if is_unqualified(callee_text) and terminal in self.module_functions:
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
        )
        for target in targets
    ]


def is_unqualified(callee_text: str) -> bool:
    return "." not in callee_text


def is_receiver_call(callee_text: str) -> bool:
    return callee_text.startswith("this.") or callee_text.startswith("super.")


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
