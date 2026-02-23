# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript call resolution utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ....tools.call_extraction import CallTarget
from .call_resolution_kernel import (
    CallResolutionAdapter,
    CallResolutionRequest,
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
        instance_map=instance_map,
        class_instance_map=class_instance_map,
    )
    return resolve_with_mode(
        shared_resolver=lambda: resolve_with_adapter(requests, adapter),
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
    instance_map: dict[str, str]
    class_instance_map: dict[str, dict[str, str]]

    def resolve(self, request: CallResolutionRequest) -> List[str]:
        terminal = request.terminal
        callee_text = request.callee_text
        receiver = request.receiver
        if "." in callee_text:
            head, rest = callee_text.split(".", 1)
            if head in self.instance_map:
                return [f"{self.instance_map[head]}.{terminal}"]
            if head in self.class_name_map:
                return [f"{self.class_name_map[head]}.{terminal}"]
            if self.class_name and (receiver == "this" or callee_text.startswith("this.")):
                chain = request.receiver_chain
                if len(chain) >= 2:
                    field = chain[1]
                    target_class = self.class_instance_map.get(self.class_name, {}).get(
                        field
                    )
                    if target_class:
                        return [f"{target_class}.{terminal}"]
            if head in self.import_aliases:
                return [f"{self.import_aliases[head]}.{rest}"]
        if terminal in self.member_aliases:
            return [self.member_aliases[terminal]]
        if (
            self.class_name
            and is_receiver_call(callee_text)
            and terminal in self.class_method_names
        ):
            return [f"{self.class_name}.{terminal}"]
        if is_unqualified(callee_text) and terminal in self.module_functions:
            return [f"{self.module_name}.{terminal}"]
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
