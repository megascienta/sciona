# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python call resolution utilities."""

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

    return resolve_with_mode(
        shared_resolver=lambda: resolve_with_adapter(requests, adapter),
    )


@dataclass(frozen=True)
class _PythonCallAdapter(CallResolutionAdapter):
    module_name: str
    module_functions: set[str]
    class_name: str | None
    class_method_names: set[str]
    import_aliases: dict[str, str]
    member_aliases: dict[str, str]
    raw_module_map: dict[str, str]
    instance_map: dict[str, str]
    class_name_candidates: dict[str, set[str]]

    def resolve(self, request: CallResolutionRequest) -> List[str]:
        terminal = request.terminal
        callee_text = request.callee_text
        receiver = request.receiver
        if "." in callee_text:
            head, rest = callee_text.split(".", 1)
            if head in self.instance_map:
                return [f"{self.instance_map[head]}.{terminal}"]
            if receiver in {"self", "cls"} or head in {"self", "cls"}:
                field = _receiver_field(callee_text)
                if field and field in self.instance_map:
                    return [f"{self.instance_map[field]}.{terminal}"]
            if head in self.import_aliases:
                return [f"{self.import_aliases[head]}.{rest}"]
            class_candidates = self.class_name_candidates.get(head) or set()
            if len(class_candidates) == 1:
                return [f"{next(iter(class_candidates))}.{terminal}"]
            if len(class_candidates) > 1:
                return []
            for raw, normalized in self.raw_module_map.items():
                if callee_text == raw or callee_text.startswith(f"{raw}."):
                    suffix = callee_text[len(raw) :].lstrip(".")
                    return [f"{normalized}.{suffix}" if suffix else normalized]
        if terminal in self.member_aliases:
            return [self.member_aliases[terminal]]
        if (
            self.class_name
            and is_self_receiver(callee_text)
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


def is_self_receiver(callee_text: str) -> bool:
    return callee_text.startswith("self.") or callee_text.startswith("cls.")
